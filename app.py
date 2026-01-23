import os
import json
import logging
import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from splunk_client import SplunkClient
from slack_handlers import parse_args, format_results
from admin_manager import AdminManager
from structured_logger import StructuredLogger


load_dotenv()  # loads .env locally (safe if .env is gitignored)

# Setup logging to both file and console
log_file = "bot.log"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler - write all logs to bot.log
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Console handler - print to terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Suppress slack_bolt debug logs from console (but keep in file)
slack_logger = logging.getLogger('slack_bolt')
slack_logger.handlers = [file_handler]
slack_logger.setLevel(logging.INFO)

# Initialize structured logger for audit trail
audit_log = StructuredLogger("bot_audit.log")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")

SPLUNK_BASE_URL = os.getenv("SPLUNK_BASE_URL", "")
SPLUNK_TOKEN = os.getenv("SPLUNK_TOKEN", "")
SPLUNK_VERIFY_TLS = os.getenv("SPLUNK_VERIFY_TLS", "true").lower() == "true"
RESULT_LIMIT = int(os.getenv("RESULT_LIMIT", "5"))

if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    raise RuntimeError("Missing SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET")

if not SPLUNK_BASE_URL or not SPLUNK_TOKEN:
    raise RuntimeError("Missing SPLUNK_BASE_URL or SPLUNK_TOKEN")

splunk = SplunkClient(base_url=SPLUNK_BASE_URL, token=SPLUNK_TOKEN, verify_tls=SPLUNK_VERIFY_TLS)

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Initialize admin manager for security
admin_manager = AdminManager()

# Setup state tracking
setup_states = {}

ENV_FILE_PATH = ".env"


def update_env_file(key: str, value: str):
    """Update .env file with new value without quotes"""
    try:
        # Read current .env file
        env_lines = []
        key_found = False
        
        if os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add the key
        for i, line in enumerate(env_lines):
            if line.startswith(f"{key}="):
                env_lines[i] = f"{key}={value}\n"
                key_found = True
                break
        
        if not key_found:
            env_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(ENV_FILE_PATH, 'w') as f:
            f.writelines(env_lines)
        
        # Reload environment
        load_dotenv(override=True)
        return True
    except Exception as e:
        print(f"Error updating .env: {e}")
        return False


def reload_admin_manager():
    """Reload admin manager after config changes"""
    global admin_manager
    admin_manager = AdminManager()


# ==================== HELP TEXT ====================

HELP_TEXT = """*🤖 Splunk Query Bot – Command Reference*

*📊 SEARCH COMMANDS:*
• `!search-alert <name>` – Run saved search
• `!search-list [contains=keyword]` – List saved searches
• `!search-info <name>` – Show search details
• `!splunk-status` – Check Splunk server health
• `!splunk-indexes` – List available indexes
• `!splunk-query "<SPL>"` – Run raw SPL query *(admin only)*

*🔍 MONITORING COMMANDS:*
• `!search-jobs` – List active search jobs *(admin only)*
• `!search-history [count]` – Show recent SPL queries *(admin only)*
• `!whoami` – Show your user info and permissions

*⚙️ CONFIGURATION COMMANDS:*
• `!setup` – Interactive bot configuration wizard
• `!config-show` – Show current configuration
• `!config-backup` – Export configuration as JSON
• `!prod-check` – Production readiness checklist

*👥 ADMIN MANAGEMENT:*
• `!admin-list` – Show all admins
• `!admin-add @user` – Add admin *(admin only)*
• `!admin-remove @user` – Remove admin *(admin only)*
• `!admin-channel-add #channel` – Allow SPL in channel
• `!admin-channel-remove #channel` – Block SPL in channel

*🔐 SECURITY COMMANDS:*
• `!security-config` – View security settings
• `!feature-toggle <feature>` – Enable/disable features
• `!audit-logs [count]` – View recent security events
• `!export-logs <json|csv|txt>` – Export audit logs *(admin only)*

*🛠️ SYSTEM COMMANDS:*
• `!system-status` – Bot health check
• `!help` – Show this message

*💡 Examples:*
• `!search-alert failed_logins earliest=-2h limit=10`
• `!search-list contains=login limit=5`
• `!splunk-indexes` → See all available indexes
• `!whoami` → Check your permissions
• `!search-history 20` → Last 20 SPL queries
"""


# ==================== SETUP WIZARD ====================

@app.message(r"^!setup\s*$")
def handle_setup(message, say):
    user_id = message.get("user", "")
    
    # Check if user is first admin or existing admin
    if admin_manager.get_admin_list() and not admin_manager.is_admin(user_id):
        say("❌ Only admins can run setup. Ask an existing admin to add you with `!admin-add @you`")
        return
    
    # If no admins exist, automatically add this user as first admin
    if not admin_manager.get_admin_list():
        admin_manager.add_admin(user_id)
        update_env_file("ADMIN_USER_IDS", user_id)
        reload_admin_manager()
        say(f"✅ You've been added as the first admin! (<@{user_id}>)")
    
    setup_states[user_id] = {"step": "start"}
    
    say(f"👋 *Welcome to Bot Setup Wizard!*\n\n"
        f"I'll help you configure this bot for your environment.\n"
        f"You can cancel anytime by typing `!setup-cancel`\n\n"
        f"*Current Setup:*\n"
        f"• Admins: {len(admin_manager.get_admin_list())}\n"
        f"• SPL Query Enabled: {admin_manager.spl_query_enabled}\n"
        f"• Result Limit: {RESULT_LIMIT}\n\n"
        f"*Step 1/5: Admin Users*\n"
        f"Who should be admins? You can:\n"
        f"• Type `!admin-add @username` to add admins\n"
        f"• Type `!admin-list` to see current admins\n"
        f"• Type `!setup-next` when done\n"
        f"*Tip:* Right-click user → Copy user ID to get format `U123456789`")


@app.message(r"^!setup-cancel\s*$")
def handle_setup_cancel(message, say):
    user_id = message.get("user", "")
    if user_id in setup_states:
        del setup_states[user_id]
        say("✅ Setup cancelled. Configuration unchanged.")
    else:
        say("No setup in progress. Use `!setup` to start.")


@app.message(r"^!setup-next\s*$")
def handle_setup_next(message, say):
    user_id = message.get("user", "")
    
    if user_id not in setup_states:
        say("No setup in progress. Use `!setup` to start.")
        return
    
    current_step = setup_states[user_id].get("step", "start")
    
    if current_step == "start":
        setup_states[user_id]["step"] = "channels"
        say(f"*Step 2/5: Channel Restrictions*\n\n"
            f"Should SPL queries be allowed in all channels or specific ones?\n"
            f"• For all channels: Type `!setup-next` (recommended for small teams)\n"
            f"• For specific channels: Use `!admin-channel-add #channel` then `!setup-next`\n"
            f"*Tip:* Right-click channel → Copy channel ID to get format `C123456789`")
    
    elif current_step == "channels":
        setup_states[user_id]["step"] = "features"
        say(f"*Step 3/5: Feature Configuration*\n\n"
            f"Configure bot features:\n"
            f"• SPL Query Feature: `!feature-toggle spl_query` (current: {admin_manager.spl_query_enabled})\n"
            f"• Approval Workflow: `!feature-toggle approval` (current: {admin_manager.approval_required})\n"
            f"When done, type `!setup-next`")
    
    elif current_step == "features":
        setup_states[user_id]["step"] = "limits"
        say(f"*Step 4/5: Result Limits*\n\n"
            f"Set default result limit (current: {RESULT_LIMIT}):\n"
            f"• Type `!config-set result_limit <number>`\n"
            f"• Or keep current and type `!setup-next`")
    
    elif current_step == "limits":
        setup_states[user_id]["step"] = "complete"
        admins_count = len(admin_manager.get_admin_list())
        channels_count = len(admin_manager.admin_channel_ids)
        
        say(f"*Step 5/5: Review & Complete*\n\n"
            f"✅ *Configuration Summary:*\n"
            f"• Admins: {admins_count}\n"
            f"• Admin Channels: {channels_count if channels_count > 0 else 'All channels'}\n"
            f"• SPL Query: {'Enabled' if admin_manager.spl_query_enabled else 'Disabled'}\n"
            f"• Approval Required: {'Yes' if admin_manager.approval_required else 'No'}\n"
            f"• Result Limit: {RESULT_LIMIT}\n\n"
            f"Type `!setup-finish` to save or `!setup-cancel` to abort")
    
    elif current_step == "complete":
        say("Setup already complete! Type `!setup-finish` to save configuration.")


@app.message(r"^!setup-finish\s*$")
def handle_setup_finish(message, say):
    user_id = message.get("user", "")
    
    if user_id not in setup_states:
        say("No setup in progress. Use `!setup` to start.")
        return
    
    del setup_states[user_id]
    say(f"🎉 *Setup Complete!*\n\n"
        f"Your bot is now configured and ready to use!\n\n"
        f"*Next Steps:*\n"
        f"• Run `!prod-check` to verify production readiness\n"
        f"• Run `!help` to see all commands\n"
        f"• Test with `!splunk-status`\n"
        f"• Backup config with `!config-backup`")


# ==================== ADMIN MANAGEMENT ====================

@app.message(r"^!admin-list\s*$")
def handle_admin_list(message, say):
    user_id = message.get("user", "")
    logger.info(f"!admin-list called by user: {user_id}")
    logger.info(f"Current admin list: {admin_manager.get_admin_list()}")
    
    admins = admin_manager.get_admin_list()
    
    if not admins:
        say("⚠️ No admins configured! Add admins with `!admin-add @user`")
        return
    
    admin_list = "\n".join([f"• <@{uid}>" for uid in admins])
    say(f"*👥 Admin Users ({len(admins)}):*\n{admin_list}")


@app.message(r"^!admin-add\s+.*")
def handle_admin_add(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "")
    
    # Check permission (must be existing admin or first admin)
    if admin_manager.get_admin_list() and not admin_manager.is_admin(user_id):
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!admin-add",
            channel_id=message.get("channel", ""),
            channel_name="unknown",
            action="Attempted to add admin",
            result="DENIED",
            error="User is not admin"
        )
        say("❌ Only admins can add other admins")
        return
    
    # Extract user ID from message (<@U123456789> or U123456789)
    import re
    match = re.search(r'<@(U[A-Z0-9]+)>|(?:^!admin-add\s+)(U[A-Z0-9]+)', text)
    
    if not match:
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!admin-add",
            channel_id=message.get("channel", ""),
            channel_name="unknown",
            action="Attempted to add admin",
            result="FAILED",
            error="Invalid user ID format"
        )
        say("❌ Usage: `!admin-add @username` or `!admin-add U123456789`\n"
            "*Tip:* Right-click user → Copy user ID")
        return
    
    new_admin_id = match.group(1) or match.group(2)
    
    # Add to runtime list
    admin_manager.add_admin(new_admin_id)
    
    # Update .env file
    current_admins = admin_manager.get_admin_list()
    update_env_file("ADMIN_USER_IDS", ",".join(current_admins))
    reload_admin_manager()
    
    say(f"✅ Added <@{new_admin_id}> as admin\n"
        f"*All admins:* {len(current_admins)} users")
    
    admin_manager.audit_log("ADMIN_ADDED", user_id, {"new_admin": new_admin_id})
    audit_log.log_action(
        user_id=user_id,
        user_name=message.get("username", "unknown"),
        command="!admin-add",
        channel_id=message.get("channel", ""),
        channel_name="unknown",
        action="Added new admin user",
        result="SUCCESS",
        changes={"new_admin": new_admin_id, "total_admins": len(current_admins)}
    )


@app.message(r"^!admin-remove\s+.*")
def handle_admin_remove(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "")
    
    # Check permission
    if not admin_manager.is_admin(user_id):
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!admin-remove",
            channel_id=message.get("channel", ""),
            channel_name="unknown",
            action="Attempted to remove admin",
            result="DENIED",
            error="User is not admin"
        )
        say("❌ Only admins can remove other admins")
        return
    
    # Extract user ID
    import re
    match = re.search(r'<@(U[A-Z0-9]+)>|(?:^!admin-remove\s+)(U[A-Z0-9]+)', text)
    
    if not match:
        say("❌ Usage: `!admin-remove @username` or `!admin-remove U123456789`")
        return
    
    remove_admin_id = match.group(1) or match.group(2)
    
    # Don't allow removing yourself if you're the last admin
    if remove_admin_id == user_id and len(admin_manager.get_admin_list()) == 1:
        say("❌ Cannot remove yourself as the last admin")
        return
    
    # Remove from runtime list
    admin_manager.remove_admin(remove_admin_id)
    
    # Update .env file
    current_admins = admin_manager.get_admin_list()
    update_env_file("ADMIN_USER_IDS", ",".join(current_admins))
    reload_admin_manager()
    
    say(f"✅ Removed <@{remove_admin_id}> from admins\n"
        f"*Remaining admins:* {len(current_admins)} users")
    
    admin_manager.audit_log("ADMIN_REMOVED", user_id, {"removed_admin": remove_admin_id})


@app.message(r"^!admin-channel-add\s+.*")
def handle_admin_channel_add(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can configure channel restrictions")
        return
    
    # Extract channel ID
    import re
    match = re.search(r'<#(C[A-Z0-9]+)\|.*?>|(?:^!admin-channel-add\s+)(C[A-Z0-9]+)', text)
    
    if not match:
        say("❌ Usage: `!admin-channel-add #channel` or `!admin-channel-add C123456789`\n"
            "*Tip:* Right-click channel → Copy channel ID")
        return
    
    channel_id = match.group(1) or match.group(2)
    
    # Add to list
    if channel_id not in admin_manager.admin_channel_ids:
        admin_manager.admin_channel_ids.append(channel_id)
        update_env_file("ADMIN_CHANNEL_IDS", ",".join(admin_manager.admin_channel_ids))
        reload_admin_manager()
        
        say(f"✅ Added <#{channel_id}> to allowed channels\n"
            f"*Allowed channels:* {len(admin_manager.admin_channel_ids)}")
    else:
        say(f"⚠️ Channel <#{channel_id}> already in allowed list")


@app.message(r"^!admin-channel-remove\s+.*")
def handle_admin_channel_remove(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can configure channel restrictions")
        return
    
    # Extract channel ID
    import re
    match = re.search(r'<#(C[A-Z0-9]+)\|.*?>|(?:^!admin-channel-remove\s+)(C[A-Z0-9]+)', text)
    
    if not match:
        say("❌ Usage: `!admin-channel-remove #channel` or `!admin-channel-remove C123456789`")
        return
    
    channel_id = match.group(1) or match.group(2)
    
    if channel_id in admin_manager.admin_channel_ids:
        admin_manager.admin_channel_ids.remove(channel_id)
        update_env_file("ADMIN_CHANNEL_IDS", ",".join(admin_manager.admin_channel_ids))
        reload_admin_manager()
        
        say(f"✅ Removed <#{channel_id}> from allowed channels\n"
            f"*Allowed channels:* {len(admin_manager.admin_channel_ids)}")
    else:
        say(f"⚠️ Channel <#{channel_id}> not in allowed list")


# ==================== SECURITY & FEATURES ====================

@app.message(r"^!security-config\s*$")
def handle_security_config(message, say):
    user_id = message.get("user", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can view security configuration")
        return
    
    admins_count = len(admin_manager.get_admin_list())
    channels_count = len(admin_manager.admin_channel_ids)
    
    say(f"*🔐 Security Configuration*\n\n"
        f"*Admin Access:*\n"
        f"• Admin Users: {admins_count}\n"
        f"• Admin Channels: {channels_count if channels_count > 0 else 'All channels allowed'}\n\n"
        f"*Feature Flags:*\n"
        f"• SPL Query: {'🟢 Enabled' if admin_manager.spl_query_enabled else '🔴 Disabled'}\n"
        f"• Approval Required: {'🟢 Yes' if admin_manager.approval_required else '🔴 No'}\n\n"
        f"*Settings:*\n"
        f"• Result Limit: {RESULT_LIMIT}\n"
        f"• TLS Verification: {'🟢 Enabled' if SPLUNK_VERIFY_TLS else '🔴 Disabled (Lab mode)'}\n\n"
        f"*Commands:*\n"
        f"• Toggle features: `!feature-toggle <feature>`\n"
        f"• Manage admins: `!admin-add`, `!admin-remove`, `!admin-list`\n"
        f"• View audit log: `!audit-logs`")


@app.message(r"^!feature-toggle\s+.*")
def handle_feature_toggle(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "").replace("!feature-toggle", "").strip()
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can toggle features")
        return
    
    if not text:
        say("❌ Usage: `!feature-toggle <feature>`\n"
            "*Available features:*\n"
            "• `spl_query` - Enable/disable SPL queries\n"
            "• `approval` - Require approval for SPL queries\n\n"
            "*Example:* `!feature-toggle spl_query`")
        return
    
    feature = text.lower()
    
    if feature in ["spl_query", "spl"]:
        new_value = not admin_manager.spl_query_enabled
        update_env_file("ENABLE_SPL_QUERY", "true" if new_value else "false")
        reload_admin_manager()
        
        say(f"✅ SPL Query feature: {'🟢 Enabled' if new_value else '🔴 Disabled'}")
        admin_manager.audit_log("FEATURE_TOGGLED", user_id, {"feature": "spl_query", "new_value": new_value})
    
    elif feature in ["approval", "require_approval"]:
        new_value = not admin_manager.approval_required
        update_env_file("REQUIRE_SPL_APPROVAL", "true" if new_value else "false")
        reload_admin_manager()
        
        say(f"✅ Approval requirement: {'🟢 Enabled' if new_value else '🔴 Disabled'}")
        admin_manager.audit_log("FEATURE_TOGGLED", user_id, {"feature": "approval", "new_value": new_value})
    
    else:
        say(f"❌ Unknown feature: `{feature}`\n"
            "Available: `spl_query`, `approval`")


@app.message(r"^!audit-logs\s*.*")
def handle_audit_logs(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "").strip()
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can view audit logs")
        return
    
    # Parse optional count argument
    count = 10  # default
    if text:
        args = text.split()
        if len(args) > 1:
            try:
                count = int(args[1])
                count = min(count, 50)  # max 50 entries
            except ValueError:
                pass
    
    # Get recent logs from audit_log
    recent_logs = audit_log.get_recent_logs(count)
    
    if not recent_logs:
        say("*📋 Audit Logs*\n\n"
            "No log entries yet. Logs are created when admin commands are run.\n\n"
            "*To generate logs, try:*\n"
            "• `!admin-list` - List admins\n"
            "• `!admin-add @user` - Add admin\n"
            "• `!export-logs json` - Export logs")
        return
    
    # Format log entries
    log_output = f"*📋 Recent Audit Logs ({len(recent_logs)} entries):*\n\n"
    
    for entry in recent_logs[-count:]:
        timestamp = entry.get('timestamp', 'N/A')
        if 'T' in timestamp:
            date = timestamp.split('T')[0]
            time = timestamp.split('T')[1].split('.')[0]
            timestamp = f"{date} {time}"
        
        result_icon = "✅" if entry.get('result') == "SUCCESS" else "❌" if entry.get('result') == "DENIED" else "⚠️"
        
        log_output += (
            f"*{result_icon} {entry.get('command', 'N/A')}*\n"
            f"  👤 User: `{entry.get('user_id', 'N/A')}`\n"
            f"  ⏰ Time: {timestamp}\n"
            f"  📝 Action: {entry.get('action', 'N/A')}\n"
            f"  Result: {entry.get('result', 'N/A')}\n"
        )
        
        if entry.get('changes'):
            log_output += f"  🔄 Changes: `{entry.get('changes')}`\n"
        
        if entry.get('error'):
            log_output += f"  ⚠️ Error: {entry.get('error')}\n"
        
        log_output += "\n"
    
    log_output += f"_Showing last {len(recent_logs)} of {len(audit_log.logs)} total entries_\n"
    log_output += "*Export all:* `!export-logs json|csv|txt`"
    
    say(log_output)


@app.message(r"^!export-logs\s*.*")
def handle_export_logs(message, say):
    user_id = message.get("user", "")
    channel_id = message.get("channel", "")
    text = message.get("text", "").strip()
    
    if not admin_manager.is_admin(user_id):
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!export-logs",
            channel_id=channel_id,
            channel_name="unknown",
            action="Attempted to export logs",
            result="DENIED",
            error="User is not admin"
        )
        say("❌ Only admins can export logs")
        return
    
    # Parse format (json, csv, txt)
    format_type = "json"  # default
    if text:
        args = text.split()
        if len(args) > 1:
            format_type = args[1].lower()
    
    if format_type not in ["json", "csv", "txt"]:
        say("❌ Invalid format. Use: `!export-logs <json|csv|txt>`\n"
            "*Examples:*\n"
            "• `!export-logs json` → Structured data format\n"
            "• `!export-logs csv` → Spreadsheet format\n"
            "• `!export-logs txt` → Readable text format")
        return
    
    # Export logs
    if format_type == "json":
        output_file = audit_log.export_json()
    elif format_type == "csv":
        output_file = audit_log.export_csv()
    else:  # txt
        output_file = audit_log.export_txt()
    
    if output_file:
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!export-logs",
            channel_id=channel_id,
            channel_name="unknown",
            action=f"Exported logs to {format_type.upper()}",
            result="SUCCESS",
            changes={"format": format_type, "file": output_file}
        )
        say(f"✅ Logs exported to `{output_file}`\n"
            f"*Format:* {format_type.upper()}\n"
            f"*Total entries:* {len(audit_log.logs)}\n"
            f"*File location:* `{output_file}` (in bot directory)")
    else:
        audit_log.log_action(
            user_id=user_id,
            user_name=message.get("username", "unknown"),
            command="!export-logs",
            channel_id=channel_id,
            channel_name="unknown",
            action=f"Attempted to export logs to {format_type.upper()}",
            result="FAILED",
            error="Export process failed"
        )
        say(f"❌ Failed to export logs")


# ==================== CONFIGURATION ====================

@app.message(r"^!config-show\s*$")
def handle_config_show(message, say):
    user_id = message.get("user", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can view configuration")
        return
    
    admins_count = len(admin_manager.get_admin_list())
    channels_count = len(admin_manager.admin_channel_ids)
    
    # Mask sensitive values
    masked_bot_token = SLACK_BOT_TOKEN[:10] + "..." if SLACK_BOT_TOKEN else "Not set"
    masked_splunk_token = SPLUNK_TOKEN[:20] + "..." if SPLUNK_TOKEN else "Not set"
    
    say(f"*⚙️ Current Configuration*\n\n"
        f"*Slack:*\n"
        f"• Bot Token: `{masked_bot_token}`\n"
        f"• Signing Secret: Configured\n\n"
        f"*Splunk:*\n"
        f"• URL: `{SPLUNK_BASE_URL}`\n"
        f"• Token: `{masked_splunk_token}`\n"
        f"• TLS Verification: {'Enabled' if SPLUNK_VERIFY_TLS else 'Disabled'}\n\n"
        f"*Admin & Security:*\n"
        f"• Admins: {admins_count}\n"
        f"• Admin Channels: {channels_count if channels_count > 0 else 'All'}\n"
        f"• SPL Query: {'Enabled' if admin_manager.spl_query_enabled else 'Disabled'}\n"
        f"• Approval Required: {'Yes' if admin_manager.approval_required else 'No'}\n\n"
        f"*Settings:*\n"
        f"• Result Limit: {RESULT_LIMIT}\n\n"
        f"*Commands:*\n"
        f"• Export: `!config-backup`\n"
        f"• Security: `!security-config`")


@app.message(r"^!config-backup\s*$")
def handle_config_backup(message, say):
    user_id = message.get("user", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can backup configuration")
        return
    
    config = {
        "admin_user_ids": admin_manager.get_admin_list(),
        "admin_channel_ids": admin_manager.admin_channel_ids,
        "spl_query_enabled": admin_manager.spl_query_enabled,
        "approval_required": admin_manager.approval_required,
        "result_limit": RESULT_LIMIT,
        "splunk_verify_tls": SPLUNK_VERIFY_TLS,
        "splunk_base_url": SPLUNK_BASE_URL
    }
    
    config_json = json.dumps(config, indent=2)
    
    say(f"*📦 Configuration Backup*\n\n"
        f"```{config_json}```\n\n"
        f"*Note:* Sensitive tokens not included. Copy this config and save securely.\n"
        f"*Restore:* Manually update `.env` file with these values")
    
    admin_manager.audit_log("CONFIG_BACKUP", user_id, {"timestamp": config})


@app.message(r"^!config-set\s+.*")
def handle_config_set(message, say):
    user_id = message.get("user", "")
    text = message.get("text", "").replace("!config-set", "").strip()
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can change configuration")
        return
    
    # Parse key=value
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        say("❌ Usage: `!config-set <key> <value>`\n"
            "*Example:* `!config-set result_limit 10`")
        return
    
    key, value = parts
    
    if key == "result_limit":
        try:
            new_limit = int(value)
            update_env_file("RESULT_LIMIT", str(new_limit))
            say(f"✅ Result limit set to {new_limit}\n"
                f"*Restart bot* for changes to take effect")
        except ValueError:
            say("❌ Result limit must be a number")
    else:
        say(f"❌ Unknown setting: `{key}`\n"
            "Available: `result_limit`")


@app.message(r"^!prod-check\s*$")
def handle_prod_check(message, say):
    # Get user ID - handle both direct message and app mention
    user_id = message.get("user")
    if not user_id:
        user_id = message.get("user_id")
    if not user_id and "subtype" not in message:
        user_id = ""
    
    # Debug logging
    logger.info(f"!prod-check DEBUG:")
    logger.info(f"  User ID from message: {repr(user_id)}")
    logger.info(f"  Message type: {message.get('type')}")
    logger.info(f"  Message subtype: {message.get('subtype')}")
    logger.info(f"  Admin list: {admin_manager.get_admin_list()}")
    logger.info(f"  Full message keys: {list(message.keys())}")
    if user_id:
        logger.info(f"  is_admin result: {admin_manager.is_admin(user_id)}")
    
    if not user_id or not admin_manager.is_admin(user_id):
        logger.warning(f"Admin check FAILED for user {repr(user_id)}")
        say("❌ Only admins can run production check")
        return
    
    checks = []
    score = 0
    
    # Check admins configured
    if len(admin_manager.get_admin_list()) > 0:
        checks.append("✅ Admin users configured")
        score += 1
    else:
        checks.append("❌ No admin users (use `!admin-add`)")
    
    # Check SPL restriction
    if admin_manager.spl_query_enabled and len(admin_manager.get_admin_list()) > 0:
        checks.append("✅ SPL queries restricted to admins")
        score += 1
    else:
        checks.append("⚠️ SPL queries not properly restricted")
    
    # Check TLS
    if SPLUNK_VERIFY_TLS:
        checks.append("✅ TLS certificate verification enabled")
        score += 1
    else:
        checks.append("⚠️ TLS verification disabled (lab mode)")
    
    # Check audit logging
    checks.append("✅ Audit logging enabled")
    score += 1
    
    # Check config backup
    checks.append("⚠️ Create config backup (`!config-backup`)")
    
    # Check tokens
    if SLACK_BOT_TOKEN and SPLUNK_TOKEN:
        checks.append("✅ Tokens configured")
        score += 1
    else:
        checks.append("❌ Missing tokens")
    
    max_score = 5
    status = "✅ Production Ready" if score >= 4 else "⚠️ Needs Attention" if score >= 3 else "❌ Not Production Ready"
    
    checks_text = "\n".join(checks)
    
    say(f"*🔍 Production Readiness Check*\n\n"
        f"{checks_text}\n\n"
        f"*Score:* {score}/{max_score}\n"
        f"*Status:* {status}\n\n"
        f"*Recommendations:*\n"
        f"• Configure all admin users\n"
        f"• Enable TLS for production\n"
        f"• Create configuration backup\n"
        f"• Test all commands\n"
        f"• Monitor audit logs")


# ==================== SYSTEM STATUS ====================

@app.message(r"^!system-status\s*$")
def handle_system_status(message, say):
    try:
        # Check Splunk connectivity
        splunk_info = splunk.get_server_info()
        splunk_status = f"✅ Connected (v{splunk_info['version']})"
    except Exception as e:
        splunk_status = f"❌ Disconnected: {str(e)[:50]}"
    
    admins_count = len(admin_manager.get_admin_list())
    
    say(f"*🛠️ System Status*\n\n"
        f"*Bot:*\n"
        f"• Status: ✅ Running\n"
        f"• Mode: Socket Mode\n"
        f"• Admins: {admins_count}\n\n"
        f"*Splunk:*\n"
        f"• Status: {splunk_status}\n"
        f"• URL: `{SPLUNK_BASE_URL}`\n"
        f"• TLS: {'Enabled' if SPLUNK_VERIFY_TLS else 'Disabled'}\n\n"
        f"*Features:*\n"
        f"• SPL Query: {'🟢 Enabled' if admin_manager.spl_query_enabled else '🔴 Disabled'}\n"
        f"• Result Limit: {RESULT_LIMIT}\n\n"
        f"Use `!help` for all commands")


# ==================== HELP COMMAND ====================

@app.message(r"^!help\s*$")
def handle_help(message, say):
    say(HELP_TEXT)


# ==================== SEARCH COMMANDS ====================

def run_search_and_respond(search_name: str, params: dict, respond_fn):
    earliest = params.get("earliest", "-24h")
    latest = params.get("latest", "now")
    limit = int(params.get("limit", RESULT_LIMIT))

    respond_fn(f"⏳ Running Splunk saved search: *{search_name}* (earliest={earliest}, latest={latest})")

    sid = splunk.dispatch_saved_search(search_name, earliest_time=earliest, latest_time=latest)
    done = splunk.wait_for_job(sid, max_wait_sec=35)

    if not done:
        respond_fn(f"⚠️ *{search_name}* started, but job did not finish in time.\n• SID: `{sid}`")
        return

    results = splunk.get_results(sid, count=limit)
    respond_fn(format_results(search_name, sid, results))


@app.message(r"^!search-alert\s+.*")
def handle_search_alert(message, say):
    text = message.get("text", "")
    args_text = text.replace("!search-alert", "", 1).strip()
    
    if not args_text or args_text.lower() == "help":
        say("*Usage:* `!search-alert <search_name> [earliest=-24h] [latest=now] [limit=5]`\n"
            "*Example:* `!search-alert failed_logins earliest=-2h limit=10`")
        return
    
    search_name, params = parse_args(args_text)

    if not search_name:
        say("❌ Please provide a search name")
        return

    try:
        run_search_and_respond(search_name, params, say)
    except Exception as e:
        say(f"❌ Error running saved search *{search_name}*: `{e}`")


@app.message(r"^!search-list\s*.*")
def handle_search_list(message, say):
    text = message.get("text", "").replace("!search-list", "").strip()
    search_name, params = parse_args(text)
    
    contains = search_name if search_name else None
    limit = int(params.get("limit", 20))
    
    try:
        searches = splunk.list_saved_searches(contains=contains, limit=limit)
        
        if not searches:
            say(f"❌ No saved searches found" + (f" matching '{contains}'" if contains else ""))
            return
        
        result = f"*Found {len(searches)} saved search(es):*\n"
        for search in searches[:limit]:
            desc = f" — {search['description']}" if search['description'] else ""
            result += f"• `{search['name']}`{desc}\n"
        
        say(result)
    except Exception as e:
        say(f"❌ Error listing saved searches: `{e}`")


@app.message(r"^!search-info\s+.*")
def handle_search_info(message, say):
    text = message.get("text", "").replace("!search-info", "").strip()
    search_name, params = parse_args(text)
    
    if not search_name:
        say("*Usage:* `!search-info <saved_search_name>`")
        return
    
    try:
        info = splunk.get_search_info(search_name)
        result = (
            f"*Search: {info['name']}*\n"
            f"*Owner:* {info['owner']}\n"
            f"*App:* {info['app']}\n"
            f"*Updated:* {info['updated']}\n"
            f"*Description:* {info['description']}\n"
            f"*SPL:* ```{info['search']}```"
        )
        say(result)
    except Exception as e:
        say(f"❌ Error getting search info: `{e}`")


@app.message(r"^!whoami\s*$")
def handle_whoami(message, say):
    """Show current user info and permissions"""
    user_id = message.get("user", "")
    channel_id = message.get("channel", "")
    
    is_admin = admin_manager.is_admin(user_id)
    can_spl, spl_reason = admin_manager.can_execute_spl(user_id, channel_id)
    
    status = "👑 Admin" if is_admin else "👤 User"
    spl_status = "✅ Allowed" if can_spl else "❌ Restricted"
    
    result = (
        f"*🔍 Your Info*\n"
        f"*User ID:* `{user_id}`\n"
        f"*Channel:* `{channel_id}`\n"
        f"*Role:* {status}\n"
        f"*SPL Query:* {spl_status}\n"
    )
    
    if is_admin:
        result += "\n*Admin Commands Available:*\n"
        result += "• `!splunk-query`, `!admin-add`, `!export-logs`, etc."
    else:
        result += "\n*Available Commands:*\n"
        result += "• `!search-alert`, `!search-list`, `!help`"
    
    say(result)


@app.message(r"^!search-history\s*.*")
def handle_search_history(message, say):
    """Show recent search queries by user"""
    user_id = message.get("user", "")
    text = message.get("text", "").replace("!search-history", "").strip()
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can view search history")
        return
    
    # Parse optional count
    count = 10
    try:
        if text:
            count = min(int(text), 50)
    except ValueError:
        pass
    
    # Get SPL query logs from audit
    spl_logs = [
        log for log in audit_log.logs 
        if log.get('command') == '!splunk-query' or 'SPL' in log.get('action', '')
    ]
    
    if not spl_logs:
        say("*📜 Search History*\n\nNo SPL queries logged yet.")
        return
    
    result = f"*📜 Recent SPL Queries ({min(len(spl_logs), count)} of {len(spl_logs)}):*\n\n"
    
    for log in spl_logs[-count:]:
        timestamp = log.get('timestamp', 'N/A')
        if 'T' in timestamp:
            timestamp = timestamp.split('T')[0] + ' ' + timestamp.split('T')[1].split('.')[0]
        
        result_icon = "✅" if log.get('result') == "SUCCESS" else "❌"
        result += f"{result_icon} `{log.get('user_id', 'N/A')}` — {timestamp}\n"
    
    say(result)


@app.message(r"^!splunk-indexes\s*$")
def handle_splunk_indexes(message, say):
    """List available Splunk indexes"""
    try:
        url = f"{splunk.base_url}/services/data/indexes"
        resp = requests.get(
            url,
            headers=splunk._headers(),
            params={"output_mode": "json", "count": 50},
            verify=splunk.verify_tls,
            timeout=splunk.timeout
        )
        resp.raise_for_status()
        
        payload = resp.json()
        indexes = []
        
        for entry in payload.get("entry", []):
            name = entry.get("name", "")
            content = entry.get("content", {})
            total_size = content.get("totalEventCount", 0)
            
            # Skip internal indexes unless they have data
            if not name.startswith("_") or total_size > 0:
                indexes.append({
                    "name": name,
                    "events": total_size
                })
        
        # Sort by event count
        indexes.sort(key=lambda x: x["events"], reverse=True)
        
        result = f"*📊 Available Indexes ({len(indexes)}):*\n\n"
        for idx in indexes[:20]:
            events = f"{idx['events']:,}" if idx['events'] else "0"
            result += f"• `{idx['name']}` — {events} events\n"
        
        if len(indexes) > 20:
            result += f"\n_...and {len(indexes) - 20} more_"
        
        say(result)
    except Exception as e:
        say(f"❌ Error listing indexes: `{e}`")


@app.message(r"^!search-jobs\s*$")
def handle_search_jobs(message, say):
    """List active search jobs"""
    user_id = message.get("user", "")
    
    if not admin_manager.is_admin(user_id):
        say("❌ Only admins can view search jobs")
        return
    
    try:
        url = f"{splunk.base_url}/services/search/jobs"
        resp = requests.get(
            url,
            headers=splunk._headers(),
            params={"output_mode": "json", "count": 20},
            verify=splunk.verify_tls,
            timeout=splunk.timeout
        )
        resp.raise_for_status()
        
        payload = resp.json()
        jobs = []
        
        for entry in payload.get("entry", []):
            content = entry.get("content", {})
            sid = content.get("sid", "")
            is_done = content.get("isDone", False)
            run_duration = content.get("runDuration", 0)
            event_count = content.get("eventCount", 0)
            
            jobs.append({
                "sid": sid[:20] + "..." if len(sid) > 20 else sid,
                "done": is_done,
                "duration": round(run_duration, 2),
                "events": event_count
            })
        
        if not jobs:
            say("*🔄 Active Search Jobs*\n\nNo active search jobs.")
            return
        
        result = f"*🔄 Search Jobs ({len(jobs)}):*\n\n"
        for job in jobs[:10]:
            status = "✅ Done" if job["done"] else "⏳ Running"
            result += f"• `{job['sid']}` — {status} ({job['duration']}s, {job['events']} events)\n"
        
        say(result)
    except Exception as e:
        say(f"❌ Error listing search jobs: `{e}`")


@app.message(r"^!splunk-status\s*$")
def handle_splunk_status(message, say):
    try:
        info = splunk.get_server_info()
        result = (
            f"✅ *Splunk Server Status*\n"
            f"*Version:* {info['version']}\n"
            f"*Build:* {info['build']}\n"
            f"*Roles:* {', '.join(info['server_roles']) or 'N/A'}\n"
        )
        say(result)
    except Exception as e:
        say(f"❌ Cannot reach Splunk: `{e}`")


@app.message(r"^!splunk-query\s+.*")
def handle_splunk_query(message, say):
    user_id = message.get("user", "")
    channel_id = message.get("channel", "")
    text = message.get("text", "").replace("!splunk-query", "").strip()
    
    # Check admin authorization
    is_allowed, reason = admin_manager.can_execute_spl(user_id, channel_id)
    if not is_allowed:
        say(f"{reason}")
        admin_manager.audit_log("DENIED_SPL_QUERY", user_id, {
            "reason": reason,
            "channel": channel_id,
            "query_preview": text[:50]
        })
        return
    
    if not text:
        say("*Usage:* `!splunk-query \"index=_internal | head 5\"`")
        return
    
    try:
        # Log authorized SPL query
        admin_manager.audit_log("EXECUTED_SPL_QUERY", user_id, {
            "channel": channel_id,
            "query_preview": text[:100]
        })
        
        say(f"⏳ Running SPL query...")
        sid = splunk.run_spl_query(text)
        done = splunk.wait_for_job(sid, max_wait_sec=35)
        
        if not done:
            say(f"⚠️ Query started but did not finish in time.\n• SID: `{sid}`")
            return
        
        results = splunk.get_results(sid, count=RESULT_LIMIT)
        say(f"*SPL Query Results* (SID: `{sid}`)\n```{str(results)}```")
    except Exception as e:
        say(f"❌ Error running SPL query: `{e}`")
        admin_manager.audit_log("ERROR_SPL_QUERY", user_id, {
            "error": str(e),
            "channel": channel_id
        })


# ==================== MAIN ====================

if __name__ == "__main__":
    app_token = os.getenv("SLACK_APP_TOKEN", "")
    if not app_token:
        raise RuntimeError("Missing SLACK_APP_TOKEN (xapp-***). Needed for Socket Mode.")

    print("⚡️ Splunk Query Bot starting...")
    print(f"📊 Admins configured: {len(admin_manager.get_admin_list())}")
    print(f"🔐 SPL Query enabled: {admin_manager.spl_query_enabled}")
    print(f"✅ Ready! Use !help to see all commands")
    
    SocketModeHandler(app, app_token).start()

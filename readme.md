# 🤖 Splunk Query Bot for Slack

A powerful Slack bot that runs Splunk saved searches and SPL queries directly from Slack. Features 28 commands across 6 categories with admin controls, audit logging, and export capabilities.

**Key Features:**
- 🔍 Run saved searches and raw SPL queries
- 👥 Admin-only commands with whitelist security
- 📊 Audit logging with JSON/CSV/TXT export
- ⚙️ Interactive setup wizard
- 🔐 Production-ready security controls

---

## 📋 Table of Contents

1. [Quick Start](#-quick-start)
2. [Commands](#-commands)
3. [Admin Setup](#-admin-setup)
4. [Configuration](#-configuration)
5. [Logging & Audit](#-logging--audit)
6. [Troubleshooting](#-troubleshooting)
7. [Contributing](#-contributing)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
```env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_SIGNING_SECRET=your-secret
SPLUNK_BASE_URL=https://your-splunk:8089
SPLUNK_TOKEN=Bearer your-token
ADMIN_USER_IDS=U0A9PJVP8BU
```

### 3. Run
```bash
python app.py
```

### 4. Test in Slack
```
!help
```

---

## 💬 Commands

### 📊 Search Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!search-alert <name>` | Run saved search | `!search-alert failed_logins` |
| `!search-list [filter]` | List saved searches | `!search-list contains=login` |
| `!search-info <name>` | Show search details | `!search-info my_search` |
| `!splunk-status` | Check Splunk health | `!splunk-status` |
| `!splunk-indexes` | List available indexes | `!splunk-indexes` |
| `!splunk-query "<SPL>"` | Run raw SPL query *(admin)* | `!splunk-query "index=main \| head 10"` |

### 🔍 Monitoring Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!whoami` | Show your user info & permissions | `!whoami` |
| `!search-jobs` | List active search jobs *(admin)* | `!search-jobs` |
| `!search-history [count]` | Show recent SPL queries *(admin)* | `!search-history 20` |

### ⚙️ Configuration Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!setup` | Interactive setup wizard | `!setup` |
| `!config-show` | View current configuration | `!config-show` |
| `!config-backup` | Export config as JSON | `!config-backup` |
| `!prod-check` | Production readiness check | `!prod-check` |

### 👥 Admin Management
| Command | Description | Example |
|---------|-------------|---------|
| `!admin-list` | Show all admins | `!admin-list` |
| `!admin-add @user` | Add admin *(admin)* | `!admin-add @john` |
| `!admin-remove @user` | Remove admin *(admin)* | `!admin-remove @john` |
| `!admin-channel-add #channel` | Allow SPL in channel | `!admin-channel-add #security` |
| `!admin-channel-remove #channel` | Block SPL in channel | `!admin-channel-remove #general` |

### 🔐 Security Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!security-config` | View security settings | `!security-config` |
| `!feature-toggle <feature>` | Enable/disable features | `!feature-toggle spl_query` |
| `!audit-logs [count]` | View recent security events | `!audit-logs 10` |
| `!export-logs <format>` | Export logs *(admin)* | `!export-logs json` |

### 🛠️ System Commands
| Command | Description | Example |
|---------|-------------|---------|
| `!system-status` | Bot health check | `!system-status` |
| `!help` | Show all commands | `!help` |

---

## 👑 Admin Setup

### First-Time Setup
1. Start bot: `python app.py`
2. In Slack: `!setup`
3. First user automatically becomes admin

### Add Admins Manually
**Option 1:** In Slack (if you're admin)
```
!admin-add @username
```

**Option 2:** Edit `.env`
```env
ADMIN_USER_IDS=U0A9PJVP8BU,U1234567890
```
Get user ID: Right-click user in Slack → Copy member ID

### Check Admin Status
```
!admin-list
```

---

## ⚙️ Configuration

### Required Settings (`.env`)
```env
# Slack (from api.slack.com)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Splunk
SPLUNK_BASE_URL=https://your-splunk:8089
SPLUNK_TOKEN=Bearer your-token
```

### Optional Settings
```env
# Security
ADMIN_USER_IDS=U123,U456          # Comma-separated admin IDs
ADMIN_CHANNEL_IDS=C123            # Restrict SPL to channels (empty=all)
ENABLE_SPL_QUERY=true             # Enable/disable SPL queries
REQUIRE_SPL_APPROVAL=false        # Future: approval workflow

# Behavior
SPLUNK_VERIFY_TLS=false           # Set true for production
RESULT_LIMIT=5                    # Max results per query
```

### Slack App Setup
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create new app → From scratch
3. Enable **Socket Mode** (Settings → Socket Mode)
4. Add scopes: `chat:write`, `channels:history`, `im:history`, `app_mentions:read`
5. Install to workspace
6. Copy tokens to `.env`

---

## 📊 Logging & Audit

### View Logs in Slack
```
!audit-logs        # Last 10 entries
!audit-logs 20     # Last 20 entries
```

### Export Logs
```
!export-logs json  # Machine-readable
!export-logs csv   # For Excel
!export-logs txt   # Human-readable
```

### Log Files
| File | Purpose |
|------|---------|
| `bot.log` | Debug logs |
| `bot_audit.log` | Audit trail (JSON) |
| `logs_export.*` | Exported logs |

### What Gets Logged
- ✅ Admin additions/removals
- ✅ Feature toggles
- ✅ SPL query executions
- ✅ Authorization denials
- ✅ Config changes

---

## 🔧 Troubleshooting

### Bot Not Responding
```bash
# Check bot is running
python app.py

# Should see:
# ⚡️ Splunk Query Bot starting...
# Bolt app is running!
```

### "Not admin" Error
```
# Check admin list
!admin-list

# If empty, first user runs:
!setup

# Or edit .env manually:
ADMIN_USER_IDS=YOUR_USER_ID
```

### Splunk Connection Failed
```
# Test connection
!splunk-status

# Check .env settings:
SPLUNK_BASE_URL=https://your-splunk:8089
SPLUNK_TOKEN=Bearer your-token
SPLUNK_VERIFY_TLS=false  # for self-signed certs
```

### Module Not Found
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate       # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Get User ID
1. Open Slack
2. Right-click on user
3. Click "Copy member ID"
4. Format: `U0A9PJVP8BU`

---

## 📁 Project Structure

```
├── app.py               # Main bot (28 commands)
├── admin_manager.py     # Admin authorization
├── splunk_client.py     # Splunk REST API client
├── slack_handlers.py    # Message parsing
├── structured_logger.py # Audit logging
├── .env                 # Configuration (gitignored)
├── requirements.txt     # Dependencies
├── bot.log              # Debug logs
└── bot_audit.log        # Audit trail (JSON)
```

---

## 🔐 Security Checklist

Before production:
- [ ] Set `SPLUNK_VERIFY_TLS=true`
- [ ] Configure `ADMIN_USER_IDS`
- [ ] Restrict `ADMIN_CHANNEL_IDS` if needed
- [ ] Run `!prod-check` (should show all green)
- [ ] Export backup: `!config-backup`

---

## 📞 Quick Reference

```bash
# Start bot
python app.py

# In Slack - Check status
!help
!whoami
!admin-list
!splunk-status
!prod-check

# Run searches
!search-list
!search-alert <name>
!splunk-indexes
!splunk-query "index=main | head 5"

# Monitoring
!search-jobs
!search-history 10

# Admin management
!admin-add @user
!admin-remove @user

# Logs
!audit-logs 10
!export-logs json
```

---

## 🤝 Contributing

### Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd "Slack Bot + Splunk Saved Search Runner"

# 2. Create virtual environment
python -m venv venv

# 3. Activate (Windows)
.\venv\Scripts\Activate.ps1

# 3. Activate (Linux/Mac)
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy env template
cp .env.example .env

# 6. Configure .env with your test credentials
```

### Project Structure

```
├── app.py               # Main bot (message handlers, commands)
├── admin_manager.py     # Admin authorization logic
├── splunk_client.py     # Splunk REST API client
├── slack_handlers.py    # Message parsing utilities
├── structured_logger.py # Audit logging system
├── .env                 # Configuration (gitignored)
├── .env.example         # Template for .env
└── requirements.txt     # Python dependencies
```

### Code Style

- **Python 3.8+** required
- Use **type hints** for function parameters
- Follow **PEP 8** naming conventions
- Add **docstrings** to all functions
- Keep functions under 50 lines

```python
# Example style
def my_function(user_id: str, limit: int = 10) -> List[dict]:
    """
    Brief description of function.
    
    Args:
        user_id: Slack user ID
        limit: Max results to return
    
    Returns:
        List of result dictionaries
    """
    pass
```

### Adding New Commands

1. **Add message handler** in `app.py`:
```python
@app.message(r"^!my-command\s*.*")
def handle_my_command(message, say):
    user_id = message.get("user", "")
    
    # Add admin check if needed
    if not admin_manager.is_admin(user_id):
        say("❌ Admin only")
        return
    
    # Your logic here
    say("✅ Command executed!")
```

2. **Add to HELP_TEXT** in `app.py`:
```python
HELP_TEXT = """
...
• `!my-command` – Description here
...
"""
```

3. **Add audit logging** (for admin commands):
```python
audit_log.log_action(
    user_id=user_id,
    user_name=message.get("username", "unknown"),
    command="!my-command",
    channel_id=message.get("channel", ""),
    channel_name="unknown",
    action="Did something",
    result="SUCCESS",
    changes={"key": "value"}
)
```

### Adding Splunk Methods

Add to `splunk_client.py`:
```python
def my_splunk_method(self, param: str) -> dict:
    """Description"""
    url = f"{self.base_url}/services/your/endpoint"
    resp = requests.get(
        url,
        headers=self._headers(),
        params={"output_mode": "json"},
        verify=self.verify_tls,
        timeout=self.timeout
    )
    resp.raise_for_status()
    return resp.json()
```

### Testing Changes

```bash
# 1. Start bot in dev mode
python app.py

# 2. Test in Slack
!your-command

# 3. Check logs
cat bot.log
cat bot_audit.log
```

### Submitting Changes

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** following code style

3. **Test thoroughly** in Slack

4. **Commit with clear message**
   ```bash
   git add .
   git commit -m "Add: !my-command for XYZ functionality"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

### Commit Message Format

```
Add: New feature description
Fix: Bug fix description  
Update: Changed existing feature
Remove: Removed feature
Docs: Documentation only
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot token (xoxb-...) |
| `SLACK_APP_TOKEN` | Yes | App token (xapp-...) |
| `SLACK_SIGNING_SECRET` | Yes | Signing secret |
| `SPLUNK_BASE_URL` | Yes | Splunk REST API URL |
| `SPLUNK_TOKEN` | Yes | Bearer token |
| `ADMIN_USER_IDS` | No | Comma-separated admin IDs |
| `ENABLE_SPL_QUERY` | No | Enable raw SPL (default: true) |
| `SPLUNK_VERIFY_TLS` | No | Verify TLS (default: true) |

### Need Help?

- Check existing code patterns in `app.py`
- Review `admin_manager.py` for auth logic
- See `structured_logger.py` for logging examples

---

**Version:** 2.1 | **Commands:** 28 | **Last Updated:** January 24, 2026

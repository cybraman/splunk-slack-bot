# 🤖 Splunk Query Bot for Slack

A powerful Slack bot that runs Splunk saved searches and SPL queries directly from Slack. Features 28 commands across 6 categories with admin controls, audit logging, and export capabilities.

![Slack Output](Screenshots/slack_bot_output.png)

**Key Features:**
- 🔍 Run saved searches and raw SPL queries from Slack
- 👥 Admin-only commands with whitelist security
- 📊 Audit logging with JSON/CSV/TXT export
- ⚙️ Interactive setup wizard
- 🔐 Production-ready security controls

---

## 📋 Table of Contents

1. [Complete Setup Guide](#-complete-setup-guide)
   - [Part 1: Slack App Setup](#part-1-slack-app-setup)
   - [Part 2: Splunk Setup (WSL)](#part-2-splunk-setup-wsl)
   - [Part 3: Bot Installation](#part-3-bot-installation)
2. [Commands](#-commands)
3. [Admin Setup](#-admin-setup)
4. [Configuration](#-configuration)
5. [Logging & Audit](#-logging--audit)
6. [Troubleshooting](#-troubleshooting)
7. [Contributing](#-contributing)

---

## 🚀 Complete Setup Guide

This guide walks you through the complete setup from scratch.

---

### Part 1: Slack App Setup

#### Step 1: Create a New Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**

![Slack App Homepage](Screenshots/slack_app_homepage.png)

3. Choose **"From scratch"**
4. Enter app name: `Splunk Query Bot`
5. Select your workspace
6. Click **"Create App"**

![Create Slack App](Screenshots/slack_app_create.png)

---

#### Step 2: Enable Socket Mode

Socket Mode allows your bot to receive events without exposing a public URL.

1. Go to **Settings → Socket Mode**
2. Toggle **"Enable Socket Mode"** ON
3. Create an App-Level Token:
   - Token Name: `socket-token`
   - Scope: `connections:write`
4. Click **"Generate"**
5. **Copy the `xapp-...` token** (this is your `SLACK_APP_TOKEN`)

![Socket Mode](Screenshots/slackapp_socket_mode.png)

---

#### Step 3: Set Bot Permissions

1. Go to **OAuth & Permissions**
2. Scroll to **"Scopes"** section
3. Under **"Bot Token Scopes"**, add these permissions:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `channels:history` | Read channel messages |
| `im:history` | Read direct messages |
| `app_mentions:read` | Respond to @mentions |
| `users:read` | Get user info |

![Bot Permissions](Screenshots/slackapp_bot_permission.png)

---

#### Step 4: Enable Event Subscriptions

1. Go to **Event Subscriptions**
2. Toggle **"Enable Events"** ON
3. Under **"Subscribe to bot events"**, add:

| Event | Purpose |
|-------|---------|
| `message.channels` | Listen to channel messages |
| `message.im` | Listen to direct messages |
| `app_mention` | Respond when @mentioned |

4. Click **"Save Changes"**

![Event Subscriptions](Screenshots/event_subscription_slack.png)

---

#### Step 5: Install App to Workspace

1. Go to **OAuth & Permissions**
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. **Copy the `xoxb-...` token** (this is your `SLACK_BOT_TOKEN`)

![Install Bot](Screenshots/slackapp_bot_install.png)

---

#### Step 6: Get Signing Secret

1. Go to **Basic Information**
2. Scroll to **"App Credentials"**
3. **Copy the "Signing Secret"** (this is your `SLACK_SIGNING_SECRET`)

---

#### ✅ Slack Tokens Collected

You should now have:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

---

### Part 2: Splunk Setup (WSL)

#### Step 1: Download Splunk Enterprise

1. Go to [splunk.com/download](https://www.splunk.com/en_us/download.html)
2. Download **Splunk Enterprise** for Linux (.deb or .tgz)

![Splunk Download](Screenshots/splunk_download.png)

---

#### Step 2: Install Splunk on System (Ubuntu)

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Splunk (if .deb)
sudo dpkg -i splunk-*.deb

# Or extract .tgz
tar -xvzf splunk-*.tgz -C /opt

# Start Splunk
sudo /opt/splunk/bin/splunk start --accept-license

# Enable boot start
sudo /opt/splunk/bin/splunk enable boot-start
```

![Splunk Setup](Screenshots/splunk_setup.png)

---

#### Step 3: Access Splunk Web UI

1. Get your Host IP:
```bash
hostname -I
```

2. Open browser: `http://<Host_IP>:8000`
3. Login with admin credentials you set during installation

---

#### Step 4: Add Data Source (Log Ingestion)

1. Go to **Settings → Add Data**
2. Choose **"Monitor"** for local files
3. Select log directory (e.g., `/var/log`)
4. Set Source Type and Index
5. Click **"Save"**

![Data Source](Screenshots/splunk_data_source.png)
![Data Source 2](Screenshots/splunk_data_source2.png)

For Linux system logs:

![Linux Log Setup](Screenshots/splunk_linux_log_setup.png)

---

#### Step 5: Create a Saved Search (Report)

1. Go to **Search & Reporting**
2. Run a search query:
```spl
index=main | head 100
```
3. Click **"Save As → Report"**
4. Name it (e.g., `demo_search`)
5. Click **"Save"**

![Splunk Search](Screenshots/splunk_search_dasboard.png)
![Saved Search](Screenshots/splunk_saved_search.png)
![Demo Search](Screenshots/saved_demo_search.png)

---

#### Step 6: Create API Token

1. Go to **Settings → Tokens** (or **Settings → Users → your_user → Edit → Tokens**)
2. Click **"New Token"**
3. Set:
   - Token Name: `slack-bot-token`
   - Audience: Leave default
   - Expiration: Set as needed
4. Click **"Create"**
5. **Copy the token** (this is your `SPLUNK_TOKEN`)

![Splunk Token](Screenshots/splunk_token.png)

---

#### ✅ Splunk Config Collected

You should now have:
```
SPLUNK_BASE_URL=http://<WSL_IP>:8089
SPLUNK_TOKEN=Bearer your-splunk-token
```

---

### Part 3: Bot Installation

#### Step 1: Clone Repository

```bash
git clone https://github.com/cybraman/splunk-slack-bot.git
cd splunk-slack-bot
```

---

#### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

---

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `slack-bolt` - Slack Bot framework
- `python-dotenv` - Environment variables
- `requests` - HTTP client for Splunk API

---

#### Step 4: Configure Environment

1. Copy the example file:
```bash
cp .env.example .env
```

2. Edit `.env` with your tokens:
```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# Splunk Configuration
SPLUNK_BASE_URL=http://172.x.x.x:8089
SPLUNK_TOKEN=Bearer your-splunk-token
SPLUNK_VERIFY_TLS=false

# Admin Configuration
ADMIN_USER_IDS=U0A9PJVP8BU
ENABLE_SPL_QUERY=true
```

---

#### Step 5: Run the Bot

```bash
python app.py
```

You should see:
```
⚡️ Splunk Query Bot starting...
📊 Admins configured: 1
🔐 SPL Query enabled: True
✅ Ready! Use !help to see all commands
Bolt app is running!
```

---

#### Step 6: Test in Slack

1. Open Slack
2. Invite bot to a channel: `/invite @Splunk Query Bot`
3. Type: `!help`
4. Run your saved search:
```
!search-alert demo_search
```

![Bot Output](Screenshots/slack_bot_output.png)

---

#### ✅ Setup Complete!

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

![API Troubleshooting](Screenshots/api_endpoint_troubleshooting.png)

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
├── .env.example         # Config template
├── requirements.txt     # Dependencies
├── bot.log              # Debug logs
├── bot_audit.log        # Audit trail (JSON)
└── Screenshots/         # Setup guide images
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
git clone https://github.com/cybraman/splunk-slack-bot.git
cd splunk-slack-bot

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

### Code Style

- **Python 3.8+** required
- Use **type hints** for function parameters
- Follow **PEP 8** naming conventions
- Add **docstrings** to all functions

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

2. **Add to HELP_TEXT** in `app.py`

3. **Add audit logging** (for admin commands)

### Commit Message Format

```
Add: New feature description
Fix: Bug fix description  
Update: Changed existing feature
Remove: Removed feature
Docs: Documentation only
```

---

## 📸 Screenshots

| Screenshot | Description |
|------------|-------------|
| ![Dashboard](Screenshots/splunk_dashboard.png) | Splunk Dashboard |
| ![Output](Screenshots/slack_bot_output.png) | Bot Output in Slack |

---

**Version:** 2.1 | **Commands:** 28 | **Last Updated:** January 24, 2026

**Author:** [cybraman](https://github.com/cybraman)

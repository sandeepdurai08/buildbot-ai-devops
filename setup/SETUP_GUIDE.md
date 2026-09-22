# 🚀 BuildBot Ultimate - Complete Setup Guide

## Quick Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SETUP STEPS                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Step 1: Install Python 3.10+     (3.14 recommended)                  │
│              ↓                                                          │
│   Step 2: Run install.bat          (installs packages)                 │
│              ↓                                                          │
│   Step 3: Get Jenkins Token        (from Jenkins UI)                   │
│              ↓                                                          │
│   Step 4: Edit .env file           (add your token)                    │
│              ↓                                                          │
│   Step 5: Create Jenkins Job       (HOT_fix_job)                       │
│              ↓                                                          │
│   Step 6: Run run_buildbot.bat     (start the app!)                    │
│              ↓                                                          │
│   Step 7: Open http://localhost:8501  (enjoy! 🎉)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 What You're Setting Up

BuildBot Ultimate is an AI-powered Jenkins assistant with **10 innovative features**:

| Feature | Description |
|---------|-------------|
| 📊 Metrics Dashboard | Real-time build statistics |
| ⚡ Quick Actions | One-click common operations |
| 📋 Build Templates | Save & reuse configurations |
| ⭐ Favorites | Star frequently used jobs |
| ⌨️ Shortcuts | !h, !j, !s, !r for power users |
| 🔮 AI Predictions | ML-powered success forecasting |
| 📈 Analytics | Build trends & insights |
| ⏰ Scheduler | Cron/hourly/daily/weekly builds |
| 👥 Collaboration | @mentions, comments, reactions |
| 🔄 Rollback | Failure analysis & recovery |

---

## Step 1: Install Python

### Check if Python is Already Installed

Open PowerShell and type:
```powershell
python --version
```

If you see `Python 3.10.x` or higher, **skip to Step 2**.

### Download and Install Python

1. **Go to:** https://www.python.org/downloads/

2. **Download:** Python 3.12 or higher (3.14 recommended)

3. **Run the installer:**

   ```
   ┌─────────────────────────────────────────────────────────────────────┐
   │                                                                     │
   │   ⚠️  CRITICAL: Check these boxes!                                  │
   │                                                                     │
   │   ☑️  Install launcher for all users                                │
   │   ☑️  Add Python to PATH    ← MUST CHECK THIS!                      │
   │                                                                     │
   │   Then click: [Install Now]                                         │
   │                                                                     │
   └─────────────────────────────────────────────────────────────────────┘
   ```

4. **Verify installation:**
   ```powershell
   python --version
   pip --version
   ```

---

## Step 2: Run Installation Script

1. **Navigate to setup folder:**
   ```
   D:\ai module\New-task1-AI devops\setup\
   ```

2. **Double-click:** `install.bat`

   This will:
   - ✅ Check Python installation
   - ✅ Install required packages (streamlit, httpx, pydantic, etc.)
   - ✅ Create .env configuration file
   - ✅ Open .env for you to edit

3. **Wait for completion** (2-5 minutes)

### Manual Installation (if needed)

```powershell
cd "D:\ai module\New-task1-AI devops\buildbot"
pip install -r requirements.txt
copy .env.example .env
```

---

## Step 3: Get Jenkins API Token

Your Jenkins should be running at `http://localhost:8080`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   1. Open Jenkins: http://localhost:8080                                │
│                                                                         │
│   2. Click your username (top-right corner)                             │
│         ↓                                                               │
│   3. Click "Configure"                                                  │
│         ↓                                                               │
│   4. Scroll down to "API Token" section                                 │
│         ↓                                                               │
│   5. Click [Add new Token]                                              │
│         ↓                                                               │
│   6. Name: buildbot                                                     │
│         ↓                                                               │
│   7. Click [Generate]                                                   │
│         ↓                                                               │
│   8. 📋 COPY THE TOKEN!                                                 │
│      (You won't see it again!)                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step 4: Configure .env File

The `.env` file is in: `D:\ai module\New-task1-AI devops\buildbot\.env`

**Edit it with your values:**

```env
# ═══════════════════════════════════════════════════════════════════════
# JENKINS CONFIGURATION (REQUIRED)
# ═══════════════════════════════════════════════════════════════════════
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_API_TOKEN=paste-your-token-here    # ← PUT YOUR TOKEN HERE!
JENKINS_DEFAULT_JOB=HOT_fix_job

# ═══════════════════════════════════════════════════════════════════════
# LLM CONFIGURATION (Pre-configured for Exterro)
# ═══════════════════════════════════════════════════════════════════════
LLM_URL=https://your-llm-endpoint.example.com/v1/chat/completions
LLM_MODEL=your-model-name
LLM_VERIFY_SSL=false    # Required for expired certificate

# ═══════════════════════════════════════════════════════════════════════
# GOOGLE CHAT (Optional)
# ═══════════════════════════════════════════════════════════════════════
GCHAT_WEBHOOK_URL=

# ═══════════════════════════════════════════════════════════════════════
# EMAIL NOTIFICATIONS (Optional - for local testing use Papercut)
# ═══════════════════════════════════════════════════════════════════════
SMTP_HOST=localhost
SMTP_PORT=25
SMTP_FROM=buildbot@local.dev
SMTP_TO=team@example.com

# ═══════════════════════════════════════════════════════════════════════
# SLACK NOTIFICATIONS (Optional)
# ═══════════════════════════════════════════════════════════════════════
SLACK_WEBHOOK_URL=

# ═══════════════════════════════════════════════════════════════════════
# ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════
ARTIFACTS_SHARED_PATH=D:\shared\builds

# ═══════════════════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════════════════
ALLOWED_REPOS=github.com
```

**Quick edit:** Double-click `open_config.bat` in setup folder

---

## Step 5: Create Jenkins Job

Create a parameterized job that BuildBot can trigger:

### 5.1 Create New Job

```
Jenkins Dashboard
    ↓
[New Item]
    ↓
Enter name: HOT_fix_job
    ↓
Select: Freestyle project
    ↓
[OK]
```

### 5.2 Configure Parameters

```
☑️ Check "This project is parameterized"
    ↓
[Add Parameter] → String Parameter
    Name: GITHUB_URL
    Default Value: (leave empty)
    ↓
[Add Parameter] → String Parameter
    Name: BRANCH
    Default Value: main
```

### 5.3 Add Build Step

```
Build Steps
    ↓
[Add build step] → Execute Windows batch command
```

**Paste this script:**

```batch
@echo off
echo ========================================
echo BuildBot Ultimate - Build Execution
echo ========================================
echo.
echo Repository: %GITHUB_URL%
echo Branch: %BRANCH%
echo Build Number: %BUILD_NUMBER%
echo.
echo ----------------------------------------
echo Starting build process...
echo ----------------------------------------

timeout /t 3 /nobreak > nul
echo [1/5] Cloning repository... OK

timeout /t 2 /nobreak > nul
echo [2/5] Installing dependencies... OK

timeout /t 3 /nobreak > nul
echo [3/5] Compiling code... OK

timeout /t 2 /nobreak > nul
echo [4/5] Running tests... OK

timeout /t 1 /nobreak > nul
echo [5/5] Packaging artifacts... OK

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================

REM Create sample artifacts
mkdir artifacts 2>nul
echo Sample DLL content > artifacts\Sample.dll
echo Sample PDB content > artifacts\Sample.pdb
echo Build info > artifacts\BUILD_INFO.txt
```

### 5.4 Archive Artifacts

```
Post-build Actions
    ↓
[Add post-build action] → Archive the artifacts
    ↓
Files to archive: artifacts/**/*
```

### 5.5 Save the Job

Click **[Save]**

---

## Step 6: Start BuildBot! 🚀

1. **Double-click:** `run_buildbot.bat` in setup folder

2. **Wait for startup:**
   ```
   You can now view your Streamlit app in your browser.
   
   Local URL: http://localhost:8501
   ```

3. **Open browser:** http://localhost:8501

---

## Step 7: Try BuildBot Ultimate!

### First Commands to Try

```
help                           # See all available commands
list jobs                      # Show Jenkins jobs
build HOT_fix_job from main    # Trigger a build
```

### Keyboard Shortcuts

```
!h    →    help
!j    →    list jobs
!s    →    show status
!r    →    rebuild last build
!a    →    show analytics
!t    →    show templates
!f    →    show favorites
```

### Advanced Features

```
# Scheduling
schedule daily build for HOT_fix_job at 09:00
show schedules

# Analytics
show analytics
predict success for HOT_fix_job

# Collaboration
build main @john please review
add comment "Looks good!" to build 143

# Templates
save template "Quick Hotfix" for HOT_fix_job
use template "Quick Hotfix"
```

---

## 🧪 Test Your Setup

Before running BuildBot, verify everything works:

**Double-click:** `test_connection.bat`

Expected output:
```
============================================
  1. Checking Python Version
============================================
  [OK] Python 3.14.x

============================================
  2. Checking Required Packages
============================================
  [OK] Streamlit (Web UI)
  [OK] HTTPX (HTTP client)
  [OK] Pydantic (Data validation)
  [OK] OpenAI (LLM client)
  ...

============================================
  3. Checking Jenkins Connection
============================================
  [OK] Jenkins connected!
  [OK] Found job(s):
         - HOT_fix_job

============================================
  4. Checking LLM Connection
============================================
  [OK] LLM endpoint accessible
  Note: SSL verification disabled

============================================
  SUMMARY
============================================
  [OK] All checks passed!
  
  SUCCESS! You're ready to run BuildBot Ultimate!
```

---

## 📁 Files Reference

```
setup/
├── install.bat              → Step 2: Install packages
├── open_config.bat          → Step 4: Edit .env file
├── test_connection.bat      → Test all connections
├── check_jenkins.bat        → Quick Jenkins test
├── run_buildbot.bat         → Step 6: Start BuildBot!
├── test_setup.py            → Python verification script
├── README.txt               → Quick reference
├── SETUP_GUIDE.md           → This file
└── IMPLEMENTATION_TASKS.md  → Step-by-step beginner guide

buildbot/
├── .env                     → Your configuration
├── .env.example             → Configuration template
├── app.py                   → Main Streamlit app
├── config.py                → Configuration management
├── requirements.txt         → Python dependencies
├── core/                    → Core logic modules
│   ├── processor.py         → Command processing
│   ├── models.py            → Data structures
│   ├── conversation.py      → Chat memory
│   ├── analytics.py         → Build analytics
│   ├── scheduler.py         → Build scheduling
│   ├── collaboration.py     → Team features
│   └── rollback.py          → Rollback manager
└── services/                → External integrations
    ├── jenkins_service.py   → Jenkins API
    ├── llm_service.py       → Exterro LLM
    ├── notification_service.py
    ├── github_service.py
    └── artifact_service.py
```

---

## ❓ Troubleshooting

### "Python not found"

```
Solution:
1. Download Python from https://www.python.org/downloads/
2. Run installer
3. ⚠️ CHECK "Add Python to PATH"
4. Restart PowerShell/Command Prompt
```

### "pip not found"

```powershell
# Use this instead:
python -m pip install -r requirements.txt
```

### "403 Forbidden from Jenkins"

```
Problem: Using password instead of API token

Solution:
1. Go to Jenkins → Your username → Configure
2. Generate new API Token
3. Use the token (not password) in .env file
```

### "Cannot connect to Jenkins"

```
Check:
1. Jenkins running? Open http://localhost:8080
2. Start Jenkins: java -jar jenkins.war --httpPort=8080
3. Check JENKINS_URL in .env file
```

### "Cannot connect to LLM"

```
Check:
1. Network access to your LLM endpoint
2. VPN connected (if required)
3. LLM_VERIFY_SSL=false is set (for expired cert)
```

### "SSL Certificate Error"

```
Solution:
Set in .env:
LLM_VERIFY_SSL=false

This bypasses SSL verification for the Exterro LLM
(their certificate is expired)
```

### "Module not found" errors

```powershell
# Reinstall all packages:
cd "D:\ai module\New-task1-AI devops\buildbot"
pip install -r requirements.txt
```

### "Streamlit command not found"

```powershell
# Use Python module syntax:
python -m streamlit run app.py
```

---

## 🎯 Quick Start Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   1. Install Python 3.10+ (with PATH checked)                          │
│                                                                         │
│   2. Double-click: setup\install.bat                                   │
│                                                                         │
│   3. Get Jenkins API token from Jenkins UI                             │
│                                                                         │
│   4. Paste token in .env file                                          │
│                                                                         │
│   5. Create "HOT_fix_job" job in Jenkins                               │
│                                                                         │
│   6. Double-click: setup\run_buildbot.bat                              │
│                                                                         │
│   7. Open: http://localhost:8501                                        │
│                                                                         │
│   8. Type: help                                                         │
│                                                                         │
│   9. Enjoy all 10 innovative features! 🎉                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Success Checklist

- [ ] Python 3.10+ installed (3.14 recommended)
- [ ] Python packages installed (via install.bat)
- [ ] .env file created with Jenkins token
- [ ] LLM_VERIFY_SSL=false set (for Exterro)
- [ ] Jenkins running at localhost:8080
- [ ] "HOT_fix_job" created in Jenkins
- [ ] test_connection.bat shows all green
- [ ] BuildBot opens at localhost:8501
- [ ] "help" command works
- [ ] "list jobs" shows your Jenkins jobs

---

## 🌟 Feature Quick Reference

| Shortcut | Command | Description |
|----------|---------|-------------|
| `!h` | help | Show all commands |
| `!j` | list jobs | List Jenkins jobs |
| `!s` | show status | Current build status |
| `!r` | rebuild last | Rebuild previous build |
| `!a` | show analytics | View build analytics |
| `!t` | show templates | View saved templates |
| `!f` | show favorites | View favorite jobs |

---

*BuildBot Ultimate Setup Guide v2.0 - September 2026*
*Exterro DevOps AI Challenge - Maximum Innovation Edition*

# 🔧 Jenkins Build Bot - Smart Jenkins Assistant

Jenkins Build Bot is an AI-powered chatbot that helps developers trigger builds, **view failure reasons with logs**, analyze build issues, and manage Jenkins jobs using natural language.

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   Developer: "build payments-api from hotfix/PAY-4821"                  ║
║                                                                          ║
║   BuildBot:  🔮 Predicted success: 87%                                   ║
║              ✅ Build #143 SUCCESS (2m 14s)                              ║
║              📦 Artifacts at: \\shared\builds\143\                       ║
║              📢 Notifications sent to GChat + Email                      ║
║              📊 Analytics updated                                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 🌟 10 Innovative Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | 📊 Metrics Dashboard | Real-time stats with animated cards |
| 2 | ⚡ Quick Actions | One-click common operations |
| 3 | 📋 Build Templates | Save & reuse build configurations |
| 4 | ⭐ Favorites | Star frequently used jobs |
| 5 | ⌨️ Shortcuts | !h, !j, !s, !r for power users |
| 6 | 🔮 AI Predictions | ML-powered success forecasting |
| 7 | 📈 Analytics | Build trends & insights |
| 8 | ⏰ Scheduler | Cron/hourly/daily/weekly builds |
| 9 | 👥 Collaboration | @mentions, comments, reactions |
| 10 | 🔄 Rollback | Failure analysis & recovery |

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```powershell
cd buildbot
pip install -r requirements.txt
```

### Step 2: Configure Environment

```powershell
copy .env.example .env
notepad .env
```

**Required settings:**
```env
# Jenkins (REQUIRED)
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_API_TOKEN=your-api-token-here
JENKINS_DEFAULT_JOB=HOT_fix_job

# LLM (Pre-configured for Exterro)
LLM_URL=https://your-llm-endpoint.example.com/v1/chat/completions
LLM_MODEL=your-model-name
LLM_VERIFY_SSL=false
```

### Step 3: Start Jenkins (if not running)

```powershell
java -jar jenkins.war --httpPort=8080
```

### Step 4: Run BuildBot

```powershell
streamlit run app.py
```

### Step 5: Open Browser

Navigate to: **http://localhost:8501**

---

## 💬 Commands & Examples

### Basic Commands

| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `list jobs` | List all Jenkins jobs |
| `build <job> from <branch>` | Trigger a build |
| `status` | Check current build status |
| `rebuild` | Re-run the last build |

### Keyboard Shortcuts

| Shortcut | Expands To |
|----------|------------|
| `!h` | help |
| `!j` | list jobs |
| `!s` | show status |
| `!r` | rebuild last build |
| `!a` | show analytics |
| `!t` | show templates |
| `!f` | show favorites |

### Advanced Features

```bash
# Build with prediction
build payments-api from main
# → Shows: "🔮 87% predicted success"

# Schedule recurring builds
schedule daily build for nightly-tests at 02:00
schedule weekly build for deploy-prod on monday at 09:00
show schedules

# Collaboration
build api-service from main @john please review
add comment "Looks good!" to build 143

# Analytics
show analytics
predict success for HOT_fix_job

# Templates
save template "Quick Hotfix" for HOT_fix_job
use template "Quick Hotfix"

# Rollback (after failure)
suggest rollback
rollback to 142
```

---

## ⚙️ Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JENKINS_URL` | Yes | `http://localhost:8080` | Jenkins server URL |
| `JENKINS_USER` | Yes | `admin` | Jenkins username |
| `JENKINS_API_TOKEN` | Yes | - | Jenkins API token |
| `JENKINS_DEFAULT_JOB` | No | `HOT_fix_job` | Default job name |
| `LLM_URL` | Yes | Exterro URL | LLM API endpoint |
| `LLM_MODEL` | Yes | Qwen3 | Model path |
| `LLM_VERIFY_SSL` | No | `true` | SSL verification (set `false` for expired certs) |
| `GCHAT_WEBHOOK_URL` | No | - | Google Chat webhook |
| `SLACK_WEBHOOK_URL` | No | - | Slack webhook |
| `SMTP_HOST` | No | `localhost` | Email server |
| `SMTP_PORT` | No | `25` | Email port |
| `ARTIFACTS_SHARED_PATH` | No | `D:\shared\builds` | Artifact destination |
| `ALLOWED_REPOS` | No | `github.com` | Allowed repo domains |

### Getting Jenkins API Token

1. Log into Jenkins at `http://localhost:8080`
2. Click your username (top right)
3. Click **Configure**
4. Under **API Token**, click **Add new Token**
5. Name it "buildbot" and click **Generate**
6. Copy the token to your `.env` file

---

## 🏗️ Architecture

```
buildbot/
├── app.py                      # Main Streamlit app (Ultimate UI)
├── config.py                   # Pydantic configuration
├── requirements.txt            # Python 3.14 compatible deps
├── .env                        # Your configuration
│
├── core/                       # Core logic modules
│   ├── models.py               # Data structures
│   ├── processor.py            # Command processing + shortcuts
│   ├── conversation.py         # Context-aware chat memory
│   ├── analytics.py            # Build trends & predictions
│   ├── scheduler.py            # Recurring build scheduler
│   ├── collaboration.py        # @mentions, comments, team
│   └── rollback.py             # Failure analysis & rollback
│
└── services/                   # External integrations
    ├── llm_service.py          # Exterro Qwen3 (OpenAI-compatible)
    ├── jenkins_service.py      # Jenkins REST API
    ├── notification_service.py # GChat + Email + Slack
    ├── github_service.py       # GitHub webhooks
    └── artifact_service.py     # Artifact handling
```

### Data Flow

```
User Input → Shortcut Expansion → LLM Parsing → Validation
                                                    ↓
                                            Build Prediction
                                                    ↓
                                            Jenkins Trigger
                                                    ↓
                                            Live Polling
                                                    ↓
                               ┌────────────────────┴────────────────────┐
                               ↓                                         ↓
                           SUCCESS                                   FAILURE
                               ↓                                         ↓
                      Update Analytics                          Analyze Failure
                      Copy Artifacts                           Suggest Rollback
                      Send Notifications                       Show Prevention Tips
```

---

## 📋 Feature Details

### 🔮 AI Predictions

Predicts build success before triggering:
- Historical success rate analysis
- Recent trend evaluation
- Time-of-day factors
- Branch stability metrics

```
🔮 Prediction: 87% success
   Factors: stable branch, good recent trend
   Warning: Friday deployments have higher failure rate
```

### 📊 Analytics Engine

Comprehensive build insights:
- Success rate trends over time
- Average build duration
- Failure pattern analysis
- Peak build time identification
- Job comparison rankings

### ⏰ Build Scheduler

Flexible scheduling options:
- **Once**: Single future execution
- **Hourly**: Every N hours
- **Daily**: Every day at specific time
- **Weekly**: Specific days at specific time
- **Cron**: Full cron expression support

### 👥 Collaboration

Team features:
- **@mentions**: Tag team members
- **Comments**: Add notes to builds
- **Reactions**: 👍 👎 🎉 🔥
- **Notifications**: Alert mentioned users

### 🔄 Rollback Manager

When builds fail:
- Automatic console log analysis
- Error categorization
- Last successful build detection
- One-click rollback suggestion
- Prevention tips

---

## 🔧 Jenkins Setup

### Create Parameterized Job

1. Jenkins → **New Item** → Name: `HOT_fix_job`
2. Select **Freestyle project** → OK
3. Check **This project is parameterized**
4. Add String Parameter: `GITHUB_URL`
5. Add String Parameter: `BRANCH` (default: `main`)
6. Add build step with sample script
7. Archive artifacts: `artifacts/**/*`
8. Save

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "403 Forbidden" from Jenkins | Use API Token, not password |
| "SSL Certificate Error" | Set `LLM_VERIFY_SSL=false` in .env |
| "Connection refused" to LLM | Check network/VPN access |
| Build triggers but nothing happens | Verify job name matches |
| "Module not found" | Run `pip install -r requirements.txt` |

---

## 📝 LLM System Prompt

```
You are BuildBot, a helpful assistant that parses developer build requests.
Extract structured information from natural language build requests.

RULES:
1. Return ONLY valid JSON - no markdown, no code fences
2. Extract repository URL and branch name exactly as stated
3. If information is missing, add it to the "missing" array
4. Never invent or guess URLs or branch names

OUTPUT FORMAT:
{
    "intent": "new_build|check_status|rebuild|list_jobs|help|unknown",
    "repo_url": "extracted URL or null",
    "branch": "extracted branch name or null",
    "job_name": "specific job if mentioned or null",
    "artifacts": ["specific", "files", "requested"],
    "missing": ["list of missing required fields"]
}
```

---

## 🙏 Credits

Built for the **Exterro DevOps AI Challenge - September 2026**

**Technology:**
- Python 3.14
- Streamlit
- Exterro Qwen3 LLM
- Jenkins

---

*BuildBot Ultimate v2.0 - Maximum Innovation Edition*

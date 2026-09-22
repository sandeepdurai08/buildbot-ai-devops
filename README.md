# BuildBot AI DevOps Agent

An intelligent AI-powered DevOps assistant that automates build management, deployment workflows, and CI/CD operations through natural language conversations.

## 🚀 Features

- **Natural Language Interface**: Interact with Jenkins, GitHub, and other DevOps tools using plain English
- **Intelligent Build Management**: Trigger builds, check status, and analyze failures with AI assistance
- **Multi-Channel Notifications**: Google Chat and Email integration for build alerts
- **Artifact Management**: Track and manage build artifacts across shared storage
- **Rollback Support**: Safe rollback capabilities with automated verification
- **Collaboration Tools**: Team-based workspace management and build scheduling

## 📋 Prerequisites

- Python 3.11+
- Jenkins server (local or remote)
- Access to an LLM API (OpenAI-compatible)
- Git installed
- Optional: Google Chat webhook for notifications

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/sandeepdurai08/buildbot-ai-devops.git
cd buildbot-ai-devops
```

### 2. Install Dependencies

**Windows:**
```bash
cd setup
install.bat
```

**Manual Installation:**
```bash
cd buildbot
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example configuration:
```bash
copy buildbot\.env.example buildbot\.env
```

Edit `buildbot/.env` with your settings:

```env
# Jenkins Configuration
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_API_TOKEN=your_jenkins_token

# LLM Configuration (OpenAI-compatible)
LLM_URL=https://api.openai.com/v1/chat/completions
LLM_MODEL=gpt-4
LLM_API_KEY=your_api_key

# Optional: Notifications
GCHAT_WEBHOOK_URL=your_google_chat_webhook
```

### 4. Run BuildBot

**Windows:**
```bash
cd setup
run_buildbot.bat
```

**Manual:**
```bash
cd buildbot
streamlit run app.py
```

Access the interface at: `http://localhost:8501`

## 📖 Documentation

- [Setup Guide](setup/SETUP_GUIDE.md) - Detailed installation instructions
- [Architecture](doc/ARCHITECTURE.md) - System design and components
- [Security](doc/SECURITY.md) - Security considerations
- [Implementation Tasks](setup/IMPLEMENTATION_TASKS.md) - Development roadmap

## 💡 Usage Examples

### Trigger a Build
```
"Build the hotfix branch from https://github.com/myorg/myproject"
```

### Check Build Status
```
"What's the status of build #45?"
```

### Schedule a Build
```
"Schedule a build for prod-release at 2 AM tomorrow"
```

### Analyze Failures
```
"Why did the last build fail?"
```

## 🏗️ Architecture

```
buildbot/
├── app.py                 # Streamlit UI
├── config.py              # Configuration management
├── core/                  # Core business logic
│   ├── analytics.py       # Build analytics
│   ├── collaboration.py   # Team features
│   ├── conversation.py    # Chat history
│   ├── models.py          # Data models
│   ├── processor.py       # Request processing
│   ├── rollback.py        # Rollback management
│   └── scheduler.py       # Build scheduling
└── services/              # External integrations
    ├── artifact_service.py
    ├── github_service.py
    ├── jenkins_service.py
    ├── llm_service.py
    └── notification_service.py
```

## 🔒 Security

- Credentials stored in `.env` (never committed to git)
- API token authentication for Jenkins
- SSL verification configurable for LLM endpoints
- Input validation for all external data

See [SECURITY.md](doc/SECURITY.md) for details.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is part of the Exterro DevOps AI Challenge (September 2026).

## 🆘 Support

For issues and questions:
- Check the [Setup Guide](setup/SETUP_GUIDE.md)
- Review [Implementation Tasks](setup/IMPLEMENTATION_TASKS.md)
- Open an issue on GitHub

## 🎯 Roadmap

- [x] Core conversation interface
- [x] Jenkins integration
- [x] GitHub repository validation
- [x] Build triggering and monitoring
- [x] Notification system (Google Chat, Email)
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] Plugin system for extensibility
- [ ] CI/CD pipeline templates

---

Built with ❤️ for the Exterro DevOps AI Challenge

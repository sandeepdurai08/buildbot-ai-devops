========================================================
         BUILDBOT ULTIMATE - SETUP FOLDER
========================================================

This folder contains setup and utility scripts.
The actual BuildBot application is in the "buildbot" folder.

VERSION: Ultimate Edition with 10 Innovative Features
PYTHON: 3.10+ required (3.14 recommended)


NEW TO THIS? START HERE:
========================

Open IMPLEMENTATION_TASKS.md for step-by-step instructions!
It breaks down everything into small, beginner-friendly tasks.


SETUP ORDER:
============

1. INSTALL.BAT
   - First time setup
   - Installs Python packages
   - Creates .env configuration file
   - IMPORTANT: Opens .env for you to add Jenkins token

2. OPEN_CONFIG.BAT
   - Opens the .env configuration file
   - Use this to update settings anytime

3. TEST_CONNECTION.BAT
   - Tests all connections (Jenkins, LLM)
   - Run this to verify setup is correct

4. CHECK_JENKINS.BAT
   - Quick test if Jenkins is running
   - Useful for troubleshooting

5. RUN_BUILDBOT.BAT
   - Starts the BuildBot application
   - Opens at http://localhost:8501


FEATURES INCLUDED:
==================

1. Metrics Dashboard     - Real-time build statistics
2. Quick Actions         - One-click common operations
3. Build Templates       - Save & reuse configurations
4. Favorites System      - Star frequently used jobs
5. Keyboard Shortcuts    - !h, !j, !s, !r for power users
6. AI Predictions        - ML-powered success forecasting
7. Analytics Engine      - Build trends & insights
8. Build Scheduler       - Cron/hourly/daily/weekly builds
9. Collaboration         - @mentions, comments, reactions
10. Rollback Manager     - Failure analysis & recovery


KEYBOARD SHORTCUTS:
===================

!h  ->  help
!j  ->  list jobs
!s  ->  show status
!r  ->  rebuild last build
!a  ->  show analytics
!t  ->  show templates
!f  ->  show favorites


DOCUMENTATION:
==============

IMPLEMENTATION_TASKS.md  - Step-by-step beginner guide (START HERE!)
SETUP_GUIDE.md           - Detailed setup instructions
README.txt               - This file
../doc/SECURITY.md       - Security documentation
../doc/ARCHITECTURE.md   - System architecture


QUICK START:
============

Step 1: Double-click INSTALL.BAT
Step 2: Add your Jenkins API token to the .env file
Step 3: Double-click RUN_BUILDBOT.BAT
Step 4: Open http://localhost:8501 in your browser
Step 5: Type "help" to get started!


GETTING JENKINS API TOKEN:
==========================

1. Open Jenkins at http://localhost:8080
2. Click your username (top-right)
3. Click "Configure"
4. Scroll to "API Token"
5. Click "Add new Token"
6. Name it: buildbot
7. Click "Generate"
8. COPY the token (you won't see it again!)
9. Paste it in .env file as JENKINS_API_TOKEN


FILES IN THIS FOLDER:
=====================

install.bat              - Install Python packages & create config
run_buildbot.bat         - Start the BuildBot application
test_connection.bat      - Test Jenkins & LLM connections
open_config.bat          - Edit configuration file
check_jenkins.bat        - Quick Jenkins connectivity test
test_setup.py            - Python verification script
IMPLEMENTATION_TASKS.md  - Step-by-step beginner guide
SETUP_GUIDE.md           - Detailed instructions
README.txt               - This file


CONFIGURATION NOTES:
====================

Key .env settings:

JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_API_TOKEN=your-token-here
JENKINS_DEFAULT_JOB=HOT_fix_job

LLM_URL=https://your-llm-endpoint.example.com/v1/chat/completions
LLM_MODEL=your-model-name
LLM_VERIFY_SSL=false    # Required for expired certificate


SECURITY NOTES:
===============

- NEVER commit .env file to Git
- Use API tokens, not passwords
- Only allow trusted repositories in ALLOWED_REPOS
- See ../doc/SECURITY.md for full security guide


TROUBLESHOOTING:
================

"Python not found"
  - Install Python from https://www.python.org/downloads/
  - Make sure to check "Add Python to PATH" during install

"Cannot connect to Jenkins"
  - Start Jenkins: java -jar jenkins.war --httpPort=8080
  - Open http://localhost:8080 to verify

"403 Forbidden from Jenkins"
  - You're using password instead of API token
  - Generate new API token in Jenkins

"SSL Certificate Error"
  - Set LLM_VERIFY_SSL=false in .env
  - This is needed for the Exterro LLM (expired cert)

"Module not found"
  - Run install.bat again
  - Or manually: pip install -r requirements.txt


========================================================
BuildBot Ultimate - Exterro DevOps AI Challenge Sep 2026
========================================================

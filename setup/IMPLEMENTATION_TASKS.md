# 📋 BuildBot - Implementation Tasks for Beginners

## Overview

This guide breaks down the setup into **small, manageable tasks**. Each task has:
- ✅ What to do
- 📍 Where to do it
- ✔️ How to verify it worked

**Estimated Total Time:** 45-60 minutes

---

## PHASE 1: Environment Setup (15 minutes)

### Task 1.1: Check if Python is Installed

**What:** Check if Python is already on your computer

**How:**
1. Press `Win + R`, type `powershell`, press Enter
2. Type this command and press Enter:
   ```powershell
   python --version
   ```

**Expected Result:**
- ✅ SUCCESS: Shows `Python 3.10.x` or higher → Skip to Task 1.3
- ❌ ERROR: "not recognized" or "not found" → Do Task 1.2

---

### Task 1.2: Install Python (Skip if already installed)

**What:** Download and install Python

**Steps:**
1. Open browser, go to: **https://www.python.org/downloads/**
2. Click the yellow **"Download Python 3.12.x"** button
3. Open the downloaded file (`python-3.12.x-amd64.exe`)
4. On the installer screen:
   ```
   ┌─────────────────────────────────────────────────┐
   │                                                 │
   │   ☑️ Check this box:                            │
   │      "Add Python 3.12 to PATH"                 │
   │                                                 │
   │   Then click: [Install Now]                    │
   │                                                 │
   └─────────────────────────────────────────────────┘
   ```
5. Wait for installation to complete
6. Click **Close**

**Verify:**
1. **Close** PowerShell if open
2. Open a **NEW** PowerShell window
3. Run:
   ```powershell
   python --version
   ```
   Should show: `Python 3.12.x`

---

### Task 1.3: Install BuildBot Packages

**What:** Install the Python libraries BuildBot needs

**Steps:**
1. Open PowerShell
2. Navigate to the setup folder:
   ```powershell
   cd "D:\ai module\New-task1-AI devops\setup"
   ```
3. Run the install script:
   ```powershell
   .\install.bat
   ```
4. Wait 2-5 minutes for packages to install

**Verify:**
```powershell
python -c "import streamlit; print('OK')"
```
Should print: `OK`

---

### Task 1.4: Create Shared Builds Folder

**What:** Create folder where build artifacts will be stored

**Steps:**
1. Open File Explorer
2. Go to `D:\`
3. Create new folder: `shared`
4. Inside `shared`, create folder: `builds`

**Final path:** `D:\shared\builds`

**Verify:** Folder exists at `D:\shared\builds`

---

## PHASE 2: Jenkins Setup (15 minutes)

### Task 2.1: Verify Jenkins is Running

**What:** Confirm Jenkins is accessible

**Steps:**
1. Open browser
2. Go to: **http://localhost:8080**

**Expected Result:**
- ✅ SUCCESS: Jenkins login page appears
- ❌ ERROR: Page doesn't load → Start Jenkins first

**If Jenkins isn't running:**
```powershell
cd "path\to\jenkins"
java -jar jenkins.war --httpPort=8080
```

---

### Task 2.2: Get Jenkins API Token (SECURITY CRITICAL)

**What:** Create a secure API token for BuildBot

**Why:** API tokens are more secure than passwords. They can be revoked anytime and don't expose your main password.

**Steps:**
1. Log into Jenkins at http://localhost:8080
2. Click your **username** (top-right corner)
3. Click **Configure** (left sidebar)
4. Scroll to **API Token** section
5. Click **Add new Token**
6. In the name field, type: `buildbot-token`
7. Click **Generate**
8. **IMPORTANT:** Copy the token NOW! You won't see it again!

**Where to save temporarily:**
```
Open Notepad, paste the token, save as:
D:\ai module\New-task1-AI devops\setup\MY_TOKEN.txt

⚠️ DELETE THIS FILE after adding to .env!
```

---

### Task 2.3: Create the Hotfix-Build Job

**What:** Create a Jenkins job that BuildBot can trigger

**Steps:**

**Step A: Create the job**
1. On Jenkins dashboard, click **New Item**
2. Enter name: `hotfix-build`
3. Select **Freestyle project**
4. Click **OK**

**Step B: Add parameters**
1. Check ☑️ **This project is parameterized**
2. Click **Add Parameter** → **String Parameter**
   - Name: `GITHUB_URL`
   - Default Value: (leave empty)
   - Description: `Repository URL`
3. Click **Add Parameter** → **String Parameter**
   - Name: `BRANCH`
   - Default Value: `main`
   - Description: `Branch to build`

**Step C: Add build script**
1. Scroll to **Build Steps**
2. Click **Add build step** → **Execute Windows batch command**
3. Paste this script:

```batch
@echo off
echo ================================================
echo   BUILDBOT - HOTFIX BUILD
echo ================================================
echo.
echo Repository: %GITHUB_URL%
echo Branch: %BRANCH%
echo Build Time: %DATE% %TIME%
echo ================================================
echo.

REM Validate inputs
if "%GITHUB_URL%"=="" (
    echo ERROR: GITHUB_URL is required!
    exit /b 1
)

if "%BRANCH%"=="" (
    echo ERROR: BRANCH is required!
    exit /b 1
)

echo [Step 1/4] Validating repository URL...
timeout /t 2 /nobreak > nul
echo            OK

echo [Step 2/4] Cloning branch %BRANCH%...
timeout /t 3 /nobreak > nul
echo            OK

echo [Step 3/4] Building project...
timeout /t 4 /nobreak > nul
echo            OK

echo [Step 4/4] Running tests...
timeout /t 2 /nobreak > nul
echo            OK

echo.
echo ================================================
echo   BUILD SUCCESSFUL!
echo ================================================

REM Create artifact folder
if not exist "artifacts" mkdir artifacts

REM Create sample output files
echo Build output for %BRANCH% > artifacts\output.dll
echo Debug symbols > artifacts\output.pdb
echo Build completed at %DATE% %TIME% > artifacts\build.log
```

**Step D: Archive artifacts (optional but recommended)**
1. Scroll to **Post-build Actions**
2. Click **Add post-build action** → **Archive the artifacts**
3. Files to archive: `artifacts/**/*`

**Step E: Save**
1. Click **Save** at the bottom

**Verify:**
1. Go to Jenkins dashboard
2. You should see `hotfix-build` job listed

---

### Task 2.4: Test Jenkins Job Manually

**What:** Verify the job works before connecting BuildBot

**Steps:**
1. Click on `hotfix-build` job
2. Click **Build with Parameters** (left sidebar)
3. Enter:
   - GITHUB_URL: `https://github.com/test/repo`
   - BRANCH: `main`
4. Click **Build**
5. Click the build number (e.g., #1) in Build History
6. Click **Console Output**

**Verify:**
- Build shows "BUILD SUCCESSFUL!"
- No errors in console output

---

## PHASE 3: Configuration (10 minutes)

### Task 3.1: Create .env Configuration File

**What:** Set up the secure configuration file

**Steps:**
1. Navigate to buildbot folder:
   ```
   D:\ai module\New-task1-AI devops\buildbot\
   ```
2. Find file: `.env.example`
3. Copy it and rename to: `.env`

**Using PowerShell:**
```powershell
cd "D:\ai module\New-task1-AI devops\buildbot"
Copy-Item .env.example .env
```

---

### Task 3.2: Configure .env File (SECURITY CRITICAL)

**What:** Add your credentials securely

**Steps:**
1. Open `.env` file in Notepad:
   ```powershell
   notepad "D:\ai module\New-task1-AI devops\buildbot\.env"
   ```

2. Find and update these lines:

```env
# JENKINS - Update these with YOUR values
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_API_TOKEN=paste-your-token-from-task-2.2-here
JENKINS_DEFAULT_JOB=hotfix-build

# LLM - Already configured (don't change unless needed)
LLM_URL=https://your-llm-endpoint.example.com/v1/chat/completions
LLM_MODEL=your-model-name
LLM_API_KEY=

# ARTIFACTS - Update path if different
ARTIFACTS_SHARED_PATH=D:\shared\builds

# SECURITY - Allowed repositories (comma-separated)
ALLOWED_REPOS=github.com
```

3. Save the file (Ctrl+S)

**⚠️ SECURITY REMINDER:**
- Delete `MY_TOKEN.txt` if you created it in Task 2.2
- Never commit `.env` to Git (it's in .gitignore)

---

### Task 3.3: Verify Configuration

**What:** Test that all settings are correct

**Steps:**
1. Run the test script:
   ```powershell
   cd "D:\ai module\New-task1-AI devops\setup"
   .\test_connection.bat
   ```

**Expected Output:**
```
============================================
  SUMMARY
============================================
  [OK] Python Version: PASSED
  [OK] Packages: PASSED
  [OK] Configuration: PASSED
  [OK] Jenkins: PASSED
  [OK] LLM: PASSED (or WARN if network issue)

  SUCCESS! You're ready to run BuildBot!
```

**If any test fails:**
- Read the error message
- Check the corresponding task above
- Re-run test after fixing

---

## PHASE 4: Run BuildBot (5 minutes)

### Task 4.1: Start BuildBot

**What:** Launch the BuildBot application

**Steps:**
1. Navigate to setup folder:
   ```powershell
   cd "D:\ai module\New-task1-AI devops\setup"
   ```
2. Run:
   ```powershell
   .\run_buildbot.bat
   ```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

### Task 4.2: Test BuildBot

**What:** Verify BuildBot works end-to-end

**Steps:**
1. Open browser: **http://localhost:8501**
2. Type these commands one by one:

**Test 1: Help**
```
help
```
Expected: Shows list of available commands

**Test 2: List Jobs**
```
list available jobs
```
Expected: Shows `hotfix-build` job

**Test 3: Trigger Build**
```
build https://github.com/test/repo from main
```
Expected: 
- "Build queued..."
- "Building..."
- "Build SUCCESS!"

---

## 🎉 COMPLETION CHECKLIST

Check off each item as you complete it:

### Phase 1: Environment
- [ ] Python 3.10+ installed
- [ ] Python packages installed
- [ ] `D:\shared\builds` folder created

### Phase 2: Jenkins
- [ ] Jenkins running at localhost:8080
- [ ] API token created and copied
- [ ] `hotfix-build` job created
- [ ] Job tested manually (built successfully)

### Phase 3: Configuration
- [ ] `.env` file created from `.env.example`
- [ ] Jenkins token added to `.env`
- [ ] `test_connection.bat` shows all green

### Phase 4: Run
- [ ] BuildBot starts without errors
- [ ] Can access http://localhost:8501
- [ ] "help" command works
- [ ] "list available jobs" shows hotfix-build
- [ ] Build triggers successfully

---

## 🔐 Security Checklist

Verify these security measures are in place:

- [ ] Using API token, NOT password
- [ ] `.env` file is NOT in Git (check `.gitignore`)
- [ ] `MY_TOKEN.txt` deleted (if created)
- [ ] `ALLOWED_REPOS` configured to limit allowed repositories
- [ ] Jenkins running on localhost only (not exposed to internet)

---

## ❓ Common Issues & Solutions

### Issue: "Python not found"
**Solution:** Reinstall Python, make sure to check "Add to PATH"

### Issue: "403 Forbidden from Jenkins"  
**Solution:** You used password instead of API token. Generate new token.

### Issue: "Cannot connect to Jenkins"
**Solution:** Start Jenkins: `java -jar jenkins.war --httpPort=8080`

### Issue: "Build queued but never starts"
**Solution:** Check Jenkins for stuck builds. Restart Jenkins if needed.

### Issue: "LLM connection failed"
**Solution:** Check network/VPN. The Exterro LLM requires network access.

### Issue: "SSL Certificate Error" or "certificate has expired"
**Solution:** The Exterro LLM server has an expired certificate.

**Fix:** Add this line to your `.env` file:
```env
LLM_VERIFY_SSL=false
```

Then run the test again. This bypasses SSL verification for the LLM server only.

---

## 📞 Getting Help

If stuck:
1. Re-read the task instructions carefully
2. Check the error message for clues
3. Run `test_connection.bat` to identify the problem
4. Check Jenkins logs for build issues

---

*Implementation Tasks Guide v1.0*

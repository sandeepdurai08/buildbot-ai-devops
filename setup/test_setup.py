"""
BuildBot Setup Verification Script
Run this to check if everything is configured correctly.

Usage:
    python test_setup.py
    
Or double-click: test_connection.bat
"""

import sys
import os

# Add buildbot to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'buildbot'))

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_ok(text):
    print(f"  [OK] {text}")

def print_fail(text):
    print(f"  [FAIL] {text}")

def print_warn(text):
    print(f"  [WARN] {text}")

def check_python_version():
    print_header("1. Checking Python Version")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_fail(f"Python {version.major}.{version.minor} - Need 3.10+")
        return False

def check_packages():
    print_header("2. Checking Required Packages")
    
    packages = [
        ("streamlit", "Streamlit (Web UI)"),
        ("requests", "Requests (HTTP client)"),
        ("httpx", "HTTPX (Async HTTP)"),
        ("openai", "OpenAI (LLM client)"),
        ("dotenv", "python-dotenv (Config)"),
        ("pydantic", "Pydantic (Data validation)"),
        ("pydantic_settings", "Pydantic Settings"),
        ("tenacity", "Tenacity (Retry logic)"),
    ]
    
    all_ok = True
    missing = []
    
    for package, name in packages:
        try:
            __import__(package)
            print_ok(name)
        except ImportError:
            print_fail(f"{name} - NOT INSTALLED")
            missing.append(package)
            all_ok = False
    
    if missing:
        print(f"\n  To install missing packages, run install.bat")
        print(f"  Or: pip install {' '.join(missing)}")
    
    return all_ok

def check_config():
    print_header("3. Checking Configuration")
    
    # Change to buildbot directory for config import
    original_dir = os.getcwd()
    buildbot_dir = os.path.join(os.path.dirname(__file__), '..', 'buildbot')
    os.chdir(buildbot_dir)
    
    try:
        from config import settings
        print_ok("Config loaded successfully")
        
        # Check Jenkins
        if settings.jenkins.api_token:
            print_ok(f"Jenkins URL: {settings.jenkins.url}")
            print_ok(f"Jenkins Token: configured")
        else:
            print_fail("Jenkins API token not set in .env")
        
        # Check LLM
        print_ok(f"LLM URL: {settings.llm.url}")
        print_ok(f"LLM Model: {settings.llm.model}")
        
        # Check notifications
        if settings.notifications.gchat_webhook_url:
            print_ok("Google Chat webhook: configured")
        else:
            print_warn("Google Chat webhook: not configured (optional)")
        
        os.chdir(original_dir)
        return True
    except Exception as e:
        os.chdir(original_dir)
        print_fail(f"Config error: {e}")
        print("\n  Make sure you have created .env file:")
        print("  Run install.bat or: copy .env.example .env")
        return False

def check_jenkins():
    print_header("4. Checking Jenkins Connection")
    
    # Change to buildbot directory for config import
    original_dir = os.getcwd()
    buildbot_dir = os.path.join(os.path.dirname(__file__), '..', 'buildbot')
    os.chdir(buildbot_dir)
    
    try:
        import requests
        from config import settings
        
        url = f"{settings.jenkins.url}/api/json"
        
        if settings.jenkins.api_token:
            auth = (settings.jenkins.user, settings.jenkins.api_token)
            response = requests.get(url, auth=auth, timeout=5)
        else:
            response = requests.get(url, timeout=5)
        
        os.chdir(original_dir)
        
        if response.status_code == 200:
            data = response.json()
            print_ok(f"Jenkins connected!")
            
            # List jobs
            jobs = data.get('jobs', [])
            if jobs:
                print_ok(f"Found {len(jobs)} job(s):")
                for job in jobs[:5]:
                    print(f"         - {job['name']}")
            else:
                print_warn("No jobs found. Create a 'hotfix-build' job in Jenkins.")
            return True
        else:
            print_fail(f"Jenkins returned status {response.status_code}")
            if response.status_code == 403:
                print("  Check your API token - might be incorrect")
            return False
            
    except Exception as e:
        os.chdir(original_dir)
        if "ConnectionError" in str(type(e)):
            print_fail("Cannot connect to Jenkins")
            print("  Make sure Jenkins is running at http://localhost:8080")
        else:
            print_fail(f"Jenkins error: {e}")
        return False

def check_llm():
    print_header("5. Checking LLM Connection")
    
    # Change to buildbot directory for config import
    original_dir = os.getcwd()
    buildbot_dir = os.path.join(os.path.dirname(__file__), '..', 'buildbot')
    os.chdir(buildbot_dir)
    
    try:
        import requests
        import urllib3
        from config import settings
        
        # Disable SSL warnings if verify is off
        if not settings.llm.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            print_warn("SSL verification disabled (for expired certificates)")
        
        headers = {"Content-Type": "application/json"}
        if settings.llm.api_key:
            headers["Authorization"] = f"Bearer {settings.llm.api_key}"
        
        payload = {
            "model": settings.llm.model,
            "messages": [{"role": "user", "content": "Say OK"}],
            "max_tokens": 10
        }
        
        print(f"  Testing: {settings.llm.url}")
        
        response = requests.post(
            settings.llm.url,
            headers=headers,
            json=payload,
            timeout=30,
            verify=settings.llm.verify_ssl
        )
        
        os.chdir(original_dir)
        
        if response.status_code == 200:
            print_ok("LLM connected!")
            return True
        else:
            print_warn(f"LLM returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    
    except requests.exceptions.SSLError as e:
        os.chdir(original_dir)
        print_fail("SSL Certificate Error!")
        print("")
        print("  The LLM server has an EXPIRED or invalid SSL certificate.")
        print("")
        print("  TO FIX: Add this line to your .env file:")
        print("  ─────────────────────────────────────────")
        print("  LLM_VERIFY_SSL=false")
        print("  ─────────────────────────────────────────")
        print("")
        print("  Then run this test again.")
        return False
            
    except Exception as e:
        os.chdir(original_dir)
        if "ConnectionError" in str(type(e)):
            print_fail("Cannot connect to LLM server")
            print("  Check network access to your LLM endpoint")
        else:
            print_warn(f"LLM test error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("     BUILDBOT SETUP VERIFICATION")
    print("="*60)
    
    results = []
    
    # Run checks
    results.append(("Python Version", check_python_version()))
    results.append(("Packages", check_packages()))
    results.append(("Configuration", check_config()))
    results.append(("Jenkins", check_jenkins()))
    results.append(("LLM", check_llm()))
    
    # Summary
    print_header("SUMMARY")
    
    all_passed = True
    for name, passed in results:
        if passed:
            print_ok(f"{name}: PASSED")
        else:
            print_fail(f"{name}: FAILED")
            all_passed = False
    
    print("\n")
    if all_passed:
        print("  SUCCESS! You're ready to run BuildBot!")
        print("\n  Run: run_buildbot.bat")
        print("  Then open: http://localhost:8501")
    else:
        print("  Some checks failed. Please fix the issues above.")
        print("  Run install.bat if packages are missing.")
    
    print("\n")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

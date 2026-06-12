#!/usr/bin/env python
"""
Smart Classroom — Automated Installation & Setup Script
======================================================
- Creates virtual environment (.venv) if missing.
- Upgrades pip and installs all dependencies in requirements.txt.
- Automatically generates and applies database migrations.
- Checks if a superuser is already configured (skips if yes, prompts if no).
- Works cross-platform on Windows, macOS, and Linux.
"""
import os
import sys
import subprocess
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, ".venv")

def check_superuser_exists(venv_python):
    # Runs code inside django to verify if any superuser is present.
    check_code = (
        "import django; django.setup(); "
        "from users.models import CustomUser; "
        "exists = CustomUser.objects.filter(is_superuser=True).exists(); "
        "print('SUPERUSER_EXISTS' if exists else 'SUPERUSER_MISSING')"
    )
    try:
        res = subprocess.run(
            [venv_python, "manage.py", "shell", "-c", check_code],
            capture_output=True, text=True, check=True
        )
        return "SUPERUSER_EXISTS" in res.stdout
    except Exception as e:
        print(f"[WARNING] Could not check superuser status: {e}")
        return False

def main():
    # If the --venv-stage flag is present, we are already running inside the venv Python environment.
    if "--venv-stage" in sys.argv:
        print("\n[STAGE 2] Configuring database and Django models...")
        
        # 1. Makemigrations
        print("\n>>> Generating database migrations...")
        subprocess.run([sys.executable, "manage.py", "makemigrations"], check=True)
        
        # 2. Migrate
        print("\n>>> Applying database migrations...")
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        
        # 3. Superuser creation check
        if check_superuser_exists(sys.executable):
            print("\n[OK] Admin superuser account already exists. Skipping creation.")
        else:
            print("\n[USER] No administrator (superuser) account found. Let's create one!")
            try:
                subprocess.run([sys.executable, "manage.py", "createsuperuser"], check=True)
            except KeyboardInterrupt:
                print("\n[WARNING] Superuser creation interrupted. You can create one later using: python manage.py createsuperuser")
            except Exception as e:
                print(f"\n[ERROR] Failed to create superuser: {e}")
        
        print("\n" + "=" * 60)
        print(" SMART CLASSROOM SETUP COMPLETE!")
        print("=" * 60)
        print("\nTo start your local server, run the following commands:")
        if platform.system() == "Windows":
            print("  .venv\\Scripts\\activate")
        else:
            print("  source .venv/bin/activate")
        print("  python manage.py runserver")
        print("\nThen open your browser and navigate to: http://127.0.0.1:8000")
        print("=" * 60)
        return

    # Stage 1: Check environment and install dependencies
    print("=" * 60)
    print(" Starting Smart Classroom Automated Setup")
    print("=" * 60)

    # 1. Check/Create Virtual Environment
    if not os.path.isdir(VENV_DIR):
        print("[INFO] Creating virtual environment (.venv)...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("[OK] Virtual environment created.")
        except Exception as e:
            print(f"[ERROR] Failed to create virtual environment: {e}")
            sys.exit(1)
    else:
        print("[INFO] Existing virtual environment (.venv) detected.")

    # Find the python and pip binaries inside the virtual environment
    if platform.system() == "Windows":
        venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        venv_pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(VENV_DIR, "bin", "python")
        venv_pip = os.path.join(VENV_DIR, "bin", "pip")

    # Double check that we found them
    if not os.path.isfile(venv_python) or not os.path.isfile(venv_pip):
        print(f"[ERROR] Virtual environment python or pip not found at: {venv_python}")
        sys.exit(1)

    # 2. Upgrade pip
    print("\n[INFO] Upgrading pip...")
    try:
        subprocess.run([venv_pip, "install", "--upgrade", "pip"], check=True)
    except Exception as e:
        print(f"[WARNING] Failed to upgrade pip: {e}. Continuing anyway.")

    # 3. Install requirements
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.isfile(req_path):
        print(f"\n[INFO] Installing dependencies from requirements.txt...")
        try:
            subprocess.run([venv_pip, "install", "-r", req_path], check=True)
            print("[OK] All dependencies installed successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to install dependencies: {e}")
            sys.exit(1)
    else:
        print("[WARNING] requirements.txt not found. Skipping dependency installation.")

    # 4. Re-execute setup.py using the virtual environment's python interpreter
    try:
        result = subprocess.run([venv_python, __file__, "--venv-stage"])
        sys.exit(result.returncode)
    except Exception as e:
        print(f"[ERROR] Failed to execute Stage 2 setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

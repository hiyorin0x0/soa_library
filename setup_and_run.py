"""
Setup script for running the LibCore SOA application quickly
"""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def get_working_python():
    venv_py = os.path.join(BASE, 'venv', 'Scripts', 'python.exe')
    if os.path.exists(venv_py):
        check = subprocess.run([venv_py, '--version'], capture_output=True)
        if check.returncode == 0:
            return venv_py
    return sys.executable


if __name__ == '__main__':
    print("=== LibCore University Library SOA — Quick Setup ===")
    py = get_working_python()
    os.environ['FLASK_APP'] = 'run.py'
    os.environ['FLASK_ENV'] = 'development'

    print("\n[1] Checking dependencies...")
    subprocess.run([py, '-m', 'pip', 'install', '-r', 'requirements.txt', '-q'], cwd=BASE)

    print("[2] Initializing database & sample data...")
    subprocess.run([py, 'run.py', 'seed'], cwd=BASE, env={**os.environ})

    print("\n[OK] Starting SOA Gateway & 4 Domain Services...")
    print("     Staff Portal: http://localhost:5000/login")
    print("     Public OPAC:  http://localhost:5000/catalog")
    subprocess.run([py, 'run.py', 'all'], cwd=BASE, env={**os.environ})

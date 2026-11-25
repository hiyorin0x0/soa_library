"""
Setup script for running the app quickly
"""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, cwd=BASE, **kwargs)

if __name__ == '__main__':
    print("=== Library SOA - Quick Setup ===")
    
    # Set env
    os.environ['FLASK_APP'] = 'run.py'
    os.environ['FLASK_ENV'] = 'development'
    
    venv_python = os.path.join(BASE, 'venv', 'Scripts', 'python.exe')

    print("\n[1] Installing dependencies...")
    run(f'"{venv_python}" -m pip install -r requirements.txt -q')

    print("[2] Running DB migrations...")
    run(f'"{venv_python}" -m flask --app run.py db upgrade', env={**os.environ})

    print("[3] Seeding database...")
    run(f'"{venv_python}" -m flask --app run.py seed-db', env={**os.environ})

    print("\n[OK] Setup complete! Starting server...")
    print("     Gateway: http://localhost:5000")
    print("     Services: books 5001, members 5002, loans 5003, reports 5004")
    print("     Admin: admin / Admin@123")
    run(f'"{venv_python}" run.py', env={**os.environ})

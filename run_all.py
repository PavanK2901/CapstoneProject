#!/usr/bin/env python3
"""Launcher script to start all MCP servers and FastAPI microservice."""
import subprocess
import sys
import time
import signal
import os
from common.config import (
    APPLICANT_DB_PORT,
    RISK_RULES_PORT,
    DECISION_SYNTHESIS_PORT,
    NOTIFICATION_PORT,
    FASTAPI_PORT
)

processes = []

def start_service(script_name: str, port: int, service_name: str):
    """Start a service in a subprocess."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(project_dir, script_name)
    print(f"🚀 Starting {service_name} on port {port}...")
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = project_dir
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=project_dir
        )
        processes.append((process, service_name, port))
        return process
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return None

def monitor_service(process, service_name: str, port: int):
    """Monitor service output in background."""
    import threading

    def read_stdout():
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{service_name}:{port}] {line.rstrip()}")

    def read_stderr():
        for line in iter(process.stderr.readline, ''):
            if line:
                print(f"[{service_name}:{port}] ERROR: {line.rstrip()}")

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()

def wait_for_service(port: int, timeout: int = 10):
    """Wait for a service to become ready."""
    import requests
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def cleanup(signum=None, frame=None):
    """Cleanup: terminate all child processes."""
    print("\n⏹️  Shutting down services...")
    for process, service_name, port in processes:
        try:
            process.terminate()
            process.wait(timeout=2)
            print(f"✅ {service_name} stopped")
        except:
            process.kill()
            print(f"⚠️  {service_name} force-killed")

def main():
    print("=" * 60)
    print("🏦 Loan Approval System - Multi-Agent Architecture")
    print("=" * 60)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        services = [
            ("mcp_servers/applicant_db_server.py", APPLICANT_DB_PORT, "Applicant DB"),
            ("mcp_servers/risk_rules_server.py", RISK_RULES_PORT, "Risk Rules"),
            ("mcp_servers/decision_synthesis_server.py", DECISION_SYNTHESIS_PORT, "Decision Synthesis"),
            ("mcp_servers/notification_server.py", NOTIFICATION_PORT, "Notification"),
            ("api/main.py", FASTAPI_PORT, "FastAPI")
        ]

        for script, port, name in services:
            start_service(script, port, name)
            time.sleep(0.5)

        print("\n⏳ Waiting for services to become ready...")
        time.sleep(2)

        for process, service_name, port in processes:
            monitor_service(process, service_name, port)

        for process, service_name, port in processes:
            if wait_for_service(port):
                print(f"✅ {service_name} is ready on port {port}")
            else:
                print(f"⚠️  {service_name} may not be ready")

        print("\n" + "=" * 60)
        print("🎉 All services started successfully!")
        print("=" * 60)
        print("\n📍 Endpoints:")
        print(f"   - FastAPI: http://localhost:{FASTAPI_PORT}")
        print(f"   - ApplicantDB MCP: http://localhost:{APPLICANT_DB_PORT}")
        print(f"   - RiskRules MCP: http://localhost:{RISK_RULES_PORT}")
        print(f"   - DecisionSynthesis MCP: http://localhost:{DECISION_SYNTHESIS_PORT}")
        print(f"   - Notification MCP: http://localhost:{NOTIFICATION_PORT}")
        print("\n🌐 UI (run in a separate terminal):")
        print("   streamlit run ui/app.py")
        print("\n📝 Test with curl:")
        print(f'   curl -X POST http://localhost:{FASTAPI_PORT}/applications \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"applicant_id":"TEST001","age":32,"income":85000,"employment_type":"salaried","credit_score":720,"loan_amount":250000,"tenure_months":360,"existing_liabilities":500,"location":"NY"}\'')
        print("\n🛑 Press Ctrl+C to stop all services\n")

        for process, _, _ in processes:
            process.wait()

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
        print("✅ All services shut down")
        sys.exit(0)

if __name__ == "__main__":
    main()

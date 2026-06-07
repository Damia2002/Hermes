"""Convenience launcher: starts FastAPI and Streamlit in parallel subprocesses."""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("Starting HERMES locally…\n")

    env_file = ROOT / ".env"
    if not env_file.exists():
        print("⚠️  No .env file found. Copy .env.example to .env and add your API keys.")
        print("   cp .env.example .env\n")

    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=str(ROOT),
    )
    time.sleep(2)

    ui_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/streamlit_app.py", "--server.port", "8501"],
        cwd=str(ROOT),
    )

    print("\n✅ HERMES is running:")
    print("   API:  http://localhost:8000")
    print("   UI:   http://localhost:8501")
    print("   Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop.\n")

    try:
        api_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down…")
        api_proc.terminate()
        ui_proc.terminate()


if __name__ == "__main__":
    main()

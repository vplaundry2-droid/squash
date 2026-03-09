from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = ROOT / "requirements.txt"
MAIN_FILE = ROOT / "main.py"


def command_string(parts: list[str]) -> str:
    return " ".join(parts)


def install_requirements() -> None:
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Missing requirements file: {REQUIREMENTS_FILE}")

    install_cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
    print("Installing Python dependencies...")
    print(f"$ {command_string(install_cmd)}")
    subprocess.check_call(install_cmd, cwd=str(ROOT))


def ensure_pygame() -> None:
    pygame_spec = importlib.util.find_spec("pygame")
    if pygame_spec is not None:
        return

    print("pygame is not installed yet.")
    install_requirements()


def run_game() -> None:
    if not MAIN_FILE.exists():
        raise FileNotFoundError(f"Missing game entrypoint: {MAIN_FILE}")

    print("Starting Squash Sim...")
    runpy.run_path(str(MAIN_FILE), run_name="__main__")


def main() -> None:
    ensure_pygame()
    run_game()


if __name__ == "__main__":
    main()

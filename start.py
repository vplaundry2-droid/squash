from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import runpy
import subprocess
import sys
import traceback

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Squash Sim")
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch the game in fullscreen mode (default is windowed).",
    )
    parser.add_argument(
        "--pause-on-exit",
        action="store_true",
        help="Wait for Enter before closing (helpful when launched by double-click).",
    )
    return parser.parse_args()


def should_pause(args: argparse.Namespace) -> bool:
    if args.pause_on_exit:
        return True
    # On Windows, scripts launched from Explorer close instantly after exiting.
    return os.name == "nt" and not sys.stdin.isatty()


def maybe_pause(args: argparse.Namespace, had_error: bool) -> None:
    if not should_pause(args):
        return

    message = "\nPress Enter to close this window..."
    if had_error:
        message = "\nThe game could not start. Press Enter to close this window..."

    try:
        input(message)
    except EOFError:
        pass


def main() -> None:
    args = parse_args()
    had_error = False

    try:
        os.environ["SQUASH_FULLSCREEN"] = "1" if args.fullscreen else "0"
        ensure_pygame()
        run_game()
    except Exception:
        had_error = True
        print("\nFailed to launch Squash Sim.")
        traceback.print_exc()
        print("\nQuick checks:")
        print("1) Make sure Python 3.10+ is installed.")
        print("2) Run: python -m pip install -r requirements.txt")
        print("3) Then run: python start.py")
    finally:
        maybe_pause(args, had_error)


if __name__ == "__main__":
    main()

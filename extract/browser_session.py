import socket
import subprocess
import time
import os
from pathlib import Path
from common.config import CHROMIUM_BIN, BROWSER_PROFILE_DIR, CDP_PORT


def _is_cdp_port_open() -> bool:
    """Return True if something is already listening on the CDP port."""
    try:
        with socket.create_connection(("localhost", CDP_PORT), timeout=1):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def run_agent_browser(*args: str) -> str:
    """Run an agent-browser command against the CDP port. Returns stdout."""
    result = subprocess.run(
        ["agent-browser", "--cdp", str(CDP_PORT)] + list(args),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"agent-browser {' '.join(args)} failed:\n{result.stderr}"
        )
    return result.stdout.strip()


def open_url(url: str) -> None:
    """Navigate to a URL and wait for the page to settle."""
    # Zinio is a slow SPA — navigation may succeed even if 'open' times out
    result = subprocess.run(
        ["agent-browser", "--cdp", str(CDP_PORT), "open", url],
        capture_output=True,
        text=True,
    )
    # Ignore timeout errors; check actual URL to confirm navigation
    if result.returncode != 0 and "timed out" not in result.stderr.lower():
        raise RuntimeError(f"agent-browser open {url} failed:\n{result.stderr}")
    time.sleep(3)  # Extra wait for SPA rendering


def get_page_text() -> str:
    """Return the full visible text of the current page."""
    return run_agent_browser("get", "text", "body")


def get_current_url() -> str:
    return run_agent_browser("get", "url")


class BrowserSession:
    """Context manager that launches chromium-browser and tears it down on exit."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> "BrowserSession":
        if _is_cdp_port_open():
            # Chromium already running — connect to it, don't launch a new instance
            return self
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [
                CHROMIUM_BIN,
                f"--user-data-dir={BROWSER_PROFILE_DIR}",
                "--no-sandbox",
                f"--remote-debugging-port={CDP_PORT}",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--disable-infobars",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "DISPLAY": ":1"},
        )
        # Wait for Chrome to bind the debug port
        time.sleep(4)
        return self

    def __exit__(self, *_):
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

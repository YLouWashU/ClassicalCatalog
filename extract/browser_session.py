import subprocess
import time
import signal
import os
from pathlib import Path
from common.config import CHROMIUM_BIN, BROWSER_PROFILE_DIR, CDP_PORT


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
    run_agent_browser("open", url)
    time.sleep(2)


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

"""
Configuration and constants for the Pixel 10 Pro Google One Gemini Bot.
"""

import os
from pathlib import Path


def _load_local_env() -> None:
    """Populate os.environ from a local .env file when present."""
    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Non-fatal: explicit environment variables still take priority.
        pass


_load_local_env()


def _env_flag(name: str, default: str = "0") -> bool:
    """Return True for common truthy environment variable values."""
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BOT_HEADER_MEDIA_URL = os.environ.get(
    "BOT_HEADER_MEDIA_URL",
    str(Path(__file__).resolve().parent / "assets" / "telegram" / "pixel-header.png"),
)

# ── Device specs – Google Pixel 10 Pro (Android 16) ──────────────────────────
DEVICE_MODEL = "Pixel 10 Pro"
DEVICE_BRAND = "google"
DEVICE_MANUFACTURER = "Google"
ANDROID_VERSION = "16"
ANDROID_SDK = "36"
BUILD_ID = "AP4A.250405.002"
DEVICE_ACCEPT_LANGUAGE = "en-US,en;q=0.9"
DEVICE_LOCALE = "en-US"
EMULATION_TIMEZONE_ID = os.environ.get("EMULATION_TIMEZONE_ID", "America/Los_Angeles")
EMULATION_GEO_LATITUDE = float(os.environ.get("EMULATION_GEO_LATITUDE", "37.3861"))
EMULATION_GEO_LONGITUDE = float(os.environ.get("EMULATION_GEO_LONGITUDE", "-122.0839"))
EMULATION_GEO_ACCURACY = int(os.environ.get("EMULATION_GEO_ACCURACY", "100"))

# ── Auto-detect installed Chrome version ─────────────────────────────────────
# Avoids UA/Client-Hints mismatch with the actual browser binary.
def _chrome_binary_candidates() -> list[str]:
    """Return candidate Chrome/Chromium binaries in priority order."""
    import shutil

    candidates: list[str] = []

    def _add(candidate: str | None) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    _add(os.environ.get("CHROME_BIN"))
    for binary in ("chromium", "chromium-browser", "google-chrome", "chrome", "chrome.exe"):
        _add(shutil.which(binary))

    if os.name == "nt":
        for candidate in (
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ):
            if candidate and os.path.exists(candidate):
                _add(candidate)

    return candidates


def _detect_chrome_version() -> tuple[str, int]:
    """Detect installed Chrome/Chromium version. Falls back to defaults."""
    import subprocess

    env_version = os.environ.get("CHROME_VERSION", "").strip()
    if env_version:
        try:
            return env_version, int(env_version.split(".")[0])
        except (TypeError, ValueError):
            pass

    for path in _chrome_binary_candidates():
        try:
            out = subprocess.check_output(
                [path, "--version"], stderr=subprocess.DEVNULL, timeout=5,
            ).decode().strip()
            # "Chromium 146.0.7680.80" or "Google Chrome 124.0.6367.82"
            parts = out.split()
            for part in parts:
                if "." in part and part[0].isdigit():
                    major = int(part.split(".")[0])
                    return part, major
        except Exception:
            continue
    return "124.0.6367.82", 124

CHROME_VERSION, CHROME_MAJOR_VERSION = _detect_chrome_version()

# Pool of realistic Pixel 10 Pro user-agent strings.
# Keep these browser-consistent; avoid WebView-only markers unless the
# underlying runtime is actually Android WebView.
USER_AGENT_TEMPLATES = [
    (
        "Mozilla/5.0 (Linux; Android {android}; {model}) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/{chrome} Mobile Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Linux; Android {android}; {model} Build/{build}) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/{chrome} Mobile Safari/537.36"
    ),
]

# ── Google URLs ───────────────────────────────────────────────────────────────
GMAIL_LOGIN_URL = "https://accounts.google.com/signin/v2/identifier"
GOOGLE_ONE_URL = "https://one.google.com/"
GOOGLE_ONE_OFFERS_URL = "https://one.google.com/about/plans"

# ── Gemini offer detection keywords ──────────────────────────────────────────
GEMINI_OFFER_KEYWORDS = [
    "gemini pro",
    "gemini advanced",
    "12 month",
    "12-month",
    "free trial",
    "activate",
    "get started",
    "claim offer",
    "redeem",
]

# Only accept offer links whose domain matches one of these.
# This prevents generic keywords ("activate", "get started") from
# matching unrelated links on Google pages.
OFFER_DOMAIN_WHITELIST = [
    "one.google.com",
    "gemini.google.com",
    "play.google.com",
    "accounts.google.com",
    "pay.google.com",
]

# ── Selenium / WebDriver ──────────────────────────────────────────────────────
WEBDRIVER_TIMEOUT = 30          # seconds – explicit wait
IMPLICIT_WAIT = 10              # seconds
PAGE_LOAD_TIMEOUT = 60          # seconds
HEADLESS = True                # set to False for local debugging with visible browser

# ── Proxy / Rotation ──────────────────────────────────────────────────────────
PROXY_ENABLED = _env_flag("PROXY_ENABLED", "1")
PROXY_FILE_PATH = os.environ.get(
    "PROXY_FILE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies.txt"),
)
PROXY_FAILURE_COOLDOWN_SECONDS = int(os.environ.get("PROXY_FAILURE_COOLDOWN_SECONDS", "90"))
PROXY_QUARANTINE_SECONDS = int(os.environ.get("PROXY_QUARANTINE_SECONDS", "300"))
PROXY_QUARANTINE_THRESHOLD = int(os.environ.get("PROXY_QUARANTINE_THRESHOLD", "3"))
PROXY_PRECHECK_ENABLED = _env_flag("PROXY_PRECHECK_ENABLED", "1")
PROXY_PRECHECK_TIMEOUT_SECONDS = int(os.environ.get("PROXY_PRECHECK_TIMEOUT_SECONDS", "12"))
REGENERATE_DEVICE_ON_RETRY = _env_flag("REGENERATE_DEVICE_ON_RETRY", "1")

# ── Email validation ──────────────────────────────────────────────────────────
# Leave empty to accept any valid email domain (Gmail + Google Workspace).
# Populate with specific domains to restrict, e.g. ["gmail.com", "mycompany.com"]
ALLOWED_EMAIL_DOMAINS: list[str] = []

# ── Session ───────────────────────────────────────────────────────────────────
# Session time-to-live in seconds.  After this period the session
# (including any stored credentials) is automatically purged.
SESSION_TTL_SECONDS: int = 30 * 60   # 30 minutes

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

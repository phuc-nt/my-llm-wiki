# security helpers — URL validation, safe fetch, path guards, label sanitisation
from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from my_llm_wiki.constants import OUTPUT_DIR

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_FETCH_BYTES = 52_428_800   # 50 MB hard cap for binary downloads
_MAX_TEXT_BYTES = 10_485_760    # 10 MB hard cap for HTML / text
_BLOCKED_HOSTS = {"metadata.google.internal", "metadata.google.com"}


# --- URL validation ---

def validate_url(url: str) -> str:
    """Raise ValueError if url is not http/https or targets private/internal IP."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(f"Blocked URL scheme '{parsed.scheme}' — only http and https allowed. Got: {url!r}")

    hostname = parsed.hostname
    if hostname:
        if hostname.lower() in _BLOCKED_HOSTS:
            raise ValueError(f"Blocked cloud metadata endpoint '{hostname}'. Got: {url!r}")
        try:
            infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                    raise ValueError(f"Blocked private/internal IP {addr} (from '{hostname}'). Got: {url!r}")
        except socket.gaierror:
            pass  # DNS failure surfaces later during fetch
    return url


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validates every redirect target to prevent open-redirect SSRF."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SafeRedirectHandler)


# --- safe fetch ---

def safe_fetch(url: str, max_bytes: int = _MAX_FETCH_BYTES, timeout: int = 30) -> bytes:
    """Fetch url and return raw bytes with size cap and SSRF protections."""
    validate_url(url)
    opener = _build_opener()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with opener.open(req, timeout=timeout) as resp:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and not (200 <= status < 300):
            raise urllib.error.HTTPError(url, status, f"HTTP {status}", {}, None)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(65_536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise OSError(f"Response from {url!r} exceeds {max_bytes // 1_048_576} MB limit.")
            chunks.append(chunk)
    return b"".join(chunks)


def safe_fetch_text(url: str, max_bytes: int = _MAX_TEXT_BYTES, timeout: int = 15) -> str:
    """Fetch url and return decoded UTF-8 text."""
    return safe_fetch(url, max_bytes=max_bytes, timeout=timeout).decode("utf-8", errors="replace")


# --- path validation ---

def validate_output_path(path: str | Path, base: Path | None = None) -> Path:
    """Resolve path and verify it stays inside base directory.

    Defaults to wiki-out/ relative to CWD.
    """
    if base is None:
        base = Path(OUTPUT_DIR).resolve()
    base = base.resolve()
    if not base.exists():
        raise ValueError(f"Output directory does not exist: {base}. Build the wiki first.")
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {path!r} escapes allowed directory {base}. Only paths inside {OUTPUT_DIR}/ permitted.")
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    return resolved


# --- label sanitisation ---

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_LABEL_LEN = 256


def sanitize_label(text: str) -> str:
    """Strip control characters, cap length, HTML-escape for safe embedding."""
    text = _CONTROL_CHAR_RE.sub("", text)
    if len(text) > _MAX_LABEL_LEN:
        text = text[:_MAX_LABEL_LEN]
    return html.escape(text)

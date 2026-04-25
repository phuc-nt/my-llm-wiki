# Append-only chronological record of vault activity (builds, notes, etc.)
# Lives at <vault_dir>/log.md. Provides an audit trail and grep-friendly
# history for the Karpathy "compounding artifact" loop.
from __future__ import annotations

from datetime import datetime
from pathlib import Path

_HEADER = "# Vault Activity Log\n\nAppend-only chronological record of vault operations.\n\n"


def append_log_entry(vault_dir: Path | str, op: str, desc: str) -> None:
    """Append a timestamped entry to <vault_dir>/log.md.

    Format: ## [YYYY-MM-DD HH:MM] [op] | desc

    Creates the file with a header on first call. No-op if vault_dir
    doesn't exist (caller decides whether to create it).

    Args:
        vault_dir: Path to the vault directory.
        op: Short operation label (e.g. "build", "note", "lint").
        desc: Free-form description of what happened.
    """
    vault = Path(vault_dir)
    if not vault.exists():
        return

    log = vault / "log.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## [{timestamp}] [{op}] | {desc}\n\n"

    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        log.write_text(_HEADER + entry, encoding="utf-8")

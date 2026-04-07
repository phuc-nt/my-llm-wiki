# file watcher — poll for changes and auto-rebuild graph
# Uses polling (no extra deps) — checks file mtimes every N seconds
from __future__ import annotations
import time
from pathlib import Path


def _snapshot(root: Path) -> dict[str, float]:
    """Return {relative_path: mtime} for all files under root."""
    snap: dict[str, float] = {}
    for p in root.rglob("*"):
        if p.is_file() and not any(part.startswith(".") for part in p.parts):
            try:
                snap[str(p.relative_to(root))] = p.stat().st_mtime
            except OSError:
                continue
    return snap


def _diff(old: dict[str, float], new: dict[str, float]) -> list[str]:
    """Return list of changed/added files."""
    changed = []
    for path, mtime in new.items():
        if path not in old or old[path] != mtime:
            changed.append(path)
    return changed


def watch(root: Path, interval: int = 5) -> None:
    """Watch root folder and auto-rebuild when files change.

    Runs llm-wiki pipeline on change detection. Ctrl+C to stop.
    """
    import subprocess
    import sys

    print(f"[wiki watch] Watching {root.resolve()} (poll every {interval}s)")
    print("[wiki watch] Press Ctrl+C to stop")

    prev = _snapshot(root)

    try:
        while True:
            time.sleep(interval)
            curr = _snapshot(root)
            changed = _diff(prev, curr)
            if changed:
                print(f"\n[wiki watch] {len(changed)} file(s) changed:")
                for f in changed[:5]:
                    print(f"  {f}")
                if len(changed) > 5:
                    print(f"  ... and {len(changed) - 5} more")
                print("[wiki watch] Rebuilding ...")
                subprocess.run(
                    [sys.executable, "-m", "my_llm_wiki", str(root)],
                    cwd=str(root.parent),
                )
                print("[wiki watch] Done. Watching for changes ...")
                prev = _snapshot(root)
            else:
                prev = curr
    except KeyboardInterrupt:
        print("\n[wiki watch] Stopped.")

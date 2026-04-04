#!/usr/bin/env python3
"""safe_git.py - Git operations that handle Cowork VM lock files gracefully.

ALL scheduled agents MUST use this script instead of raw git commands.
Cowork VMs create immutable .git/*.lock files that cannot be deleted,
causing agents to waste dozens of turns on workarounds.

Usage:
    python scripts/safe_git.py commit -m "message" -- file1.py file2.md
    python scripts/safe_git.py commit -m "message" --all-unstaged
    python scripts/safe_git.py status
    python scripts/safe_git.py push

If commit fails due to locks, writes a pending_commits.json manifest
that Debbie can apply from her Mac with: python scripts/safe_git.py apply
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PENDING_FILE = REPO_ROOT / "pending_commits.json"
GIT_DIR = REPO_ROOT / ".git"
MAX_LOCK_ATTEMPTS = 2


def run_git(*args, env_override=None, check=True):
    """Run a git command, return (returncode, stdout, stderr)."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if check and result.returncode != 0:
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def clear_locks():
    """Try to remove git lock files. Returns True if all cleared."""
    lock_files = list(GIT_DIR.glob("*.lock"))
    if not lock_files:
        return True

    all_cleared = True
    for lock in lock_files:
        try:
            lock.unlink()
            print(f"  [OK] Removed {lock.name}")
        except (PermissionError, OSError):
            # Try truncating (sometimes works even when unlink fails)
            try:
                lock.write_bytes(b"")
            except (PermissionError, OSError):
                pass
            all_cleared = False
            print(f"  [WARN] Cannot remove {lock.name} (immutable)")

    return all_cleared


def try_commit_with_alt_index(files, message):
    """Use GIT_INDEX_FILE trick to bypass index.lock."""
    # Copy current index to temp location
    src_index = GIT_DIR / "index"
    if not src_index.exists():
        return False, "No git index found"

    tmp_dir = tempfile.mkdtemp(prefix="safe_git_")
    tmp_index = os.path.join(tmp_dir, "index")
    shutil.copy2(str(src_index), tmp_index)

    env = {"GIT_INDEX_FILE": tmp_index}

    # Stage files using alternate index
    rc, out, err = run_git("add", *files, env_override=env, check=False)
    if rc != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False, f"git add failed: {err}"

    # Check if HEAD.lock exists (blocks commit regardless of index trick)
    head_lock = GIT_DIR / "HEAD.lock"
    if head_lock.exists():
        try:
            head_lock.unlink()
        except (PermissionError, OSError):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return False, "HEAD.lock is immutable -- commit impossible from this VM"

    # Try commit with alternate index
    rc, out, err = run_git(
        "commit", "-m", message,
        env_override=env, check=False
    )
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if rc == 0:
        return True, out
    return False, f"commit failed: {err}"


def write_pending_commit(files, message, agent_name=None):
    """Write a pending commit manifest for Debbie to apply later."""
    pending = []
    if PENDING_FILE.exists():
        try:
            pending = json.loads(PENDING_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pending = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "files": files,
        "agent": agent_name or "unknown",
        "applied": False,
    }
    pending.append(entry)
    PENDING_FILE.write_text(json.dumps(pending, indent=2))
    print(f"  [OK] Saved to pending_commits.json ({len(pending)} pending)")
    return True


def apply_pending():
    """Apply all pending commits (run from Debbie's Mac)."""
    if not PENDING_FILE.exists():
        print("No pending commits.")
        return 0

    pending = json.loads(PENDING_FILE.read_text())
    unapplied = [p for p in pending if not p.get("applied")]

    if not unapplied:
        print("All pending commits already applied.")
        return 0

    # Clear locks first (should work on real Mac)
    clear_locks()

    for i, entry in enumerate(unapplied):
        print(f"\n--- Pending commit {i+1}/{len(unapplied)} ---")
        print(f"  Agent: {entry['agent']}")
        print(f"  Message: {entry['message']}")
        print(f"  Files: {', '.join(entry['files'])}")

        rc, out, err = run_git("add", *entry["files"], check=False)
        if rc != 0:
            print(f"  [FAIL] git add: {err}")
            continue

        rc, out, err = run_git("commit", "-m", entry["message"], check=False)
        if rc == 0:
            print(f"  [OK] Committed")
            entry["applied"] = True
        else:
            print(f"  [FAIL] git commit: {err}")

    PENDING_FILE.write_text(json.dumps(pending, indent=2))
    applied = sum(1 for p in pending if p.get("applied"))
    print(f"\nApplied {applied}/{len(pending)} commits.")
    return 0


def cmd_status(_args):
    """Show git status and any pending commits."""
    locks = list(GIT_DIR.glob("*.lock"))
    if locks:
        print(f"Lock files present: {', '.join(l.name for l in locks)}")
    else:
        print("No lock files.")

    rc, out, _ = run_git("status", "--short", check=False)
    if out:
        print(f"\nModified/untracked:\n{out}")
    else:
        print("\nWorking tree clean.")

    if PENDING_FILE.exists():
        pending = json.loads(PENDING_FILE.read_text())
        unapplied = [p for p in pending if not p.get("applied")]
        if unapplied:
            print(f"\nPending commits: {len(unapplied)}")
            for p in unapplied:
                print(f"  - [{p['agent']}] {p['message']} ({len(p['files'])} files)")


def cmd_commit(args):
    """Attempt to commit files, falling back to pending manifest."""
    if not args.message:
        print("Error: -m message is required")
        return 1

    files = args.files or []
    if args.all_unstaged:
        rc, out, _ = run_git("status", "--short", check=False)
        if out:
            files = [
                line.split()[-1] for line in out.splitlines()
                if line.strip()
            ]

    if not files:
        print("No files to commit.")
        return 0

    agent_name = args.agent or os.environ.get("AGENT_NAME", "unknown")
    print(f"Committing {len(files)} files as {agent_name}...")

    # Step 1: Try to clear locks
    print("Step 1: Clearing lock files...")
    locks_clear = clear_locks()

    # Step 2: Try normal commit
    if locks_clear:
        print("Step 2: Attempting normal commit...")
        rc, out, err = run_git("add", *files, check=False)
        if rc == 0:
            rc, out, err = run_git("commit", "-m", args.message, check=False)
            if rc == 0:
                print(f"  [OK] Committed: {out.splitlines()[0] if out else 'done'}")
                return 0
            elif "nothing to commit" in err or "nothing to commit" in out:
                print("  [OK] Nothing to commit (files already match HEAD)")
                return 0

    # Step 3: Try alternate index trick
    print("Step 3: Attempting alternate index commit...")
    success, detail = try_commit_with_alt_index(files, args.message)
    if success:
        print(f"  [OK] Committed via alternate index: {detail.splitlines()[0] if detail else 'done'}")
        return 0
    else:
        print(f"  [FAIL] {detail}")

    # Step 4: Write pending manifest
    print("Step 4: Writing pending commit manifest...")
    write_pending_commit(files, args.message, agent_name)
    print(
        "\n  Git commit blocked by immutable lock files."
        "\n  Debbie: run 'python scripts/safe_git.py apply' from your Mac to commit."
    )
    return 0


def cmd_push(_args):
    """Attempt to push (will fail from Cowork VM, that's expected)."""
    rc, out, err = run_git("push", "origin", "master", check=False)
    if rc == 0:
        print(f"  [OK] Pushed to origin/master")
    else:
        if "Authentication" in err or "credential" in err or "fatal" in err:
            print("  [INFO] Push failed (no credentials -- expected from Cowork VM).")
            print("  Debbie: run 'git push origin master' from your Mac.")
        else:
            print(f"  [FAIL] {err}")
    return 0


def cmd_apply(_args):
    """Apply pending commits (for Debbie on her Mac)."""
    return apply_pending()


def main():
    parser = argparse.ArgumentParser(
        description="Safe git operations for Cowork VM agents"
    )
    sub = parser.add_subparsers(dest="command")

    # commit
    p_commit = sub.add_parser("commit", help="Stage and commit files")
    p_commit.add_argument("-m", "--message", required=True, help="Commit message")
    p_commit.add_argument("--agent", help="Agent name (default: $AGENT_NAME or 'unknown')")
    p_commit.add_argument("--all-unstaged", action="store_true", help="Commit all modified/untracked files")
    p_commit.add_argument("files", nargs="*", help="Files to commit")

    # status
    sub.add_parser("status", help="Show git status and pending commits")

    # push
    sub.add_parser("push", help="Attempt to push to origin")

    # apply
    sub.add_parser("apply", help="Apply pending commits (Debbie's Mac)")

    args = parser.parse_args()

    if args.command == "commit":
        return cmd_commit(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "push":
        return cmd_push(args)
    elif args.command == "apply":
        return cmd_apply(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)

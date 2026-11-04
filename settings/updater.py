"""Checks GitHub for a newer release (a v1.2.3 tag) and fast-forwards this folder to it.

Uses the git already set up here (so a private repo works with your own credentials); nothing is
downloaded outside git, and an update never overwrites changes you've made (it refuses instead)."""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r"^refs/tags/v(\d+)\.(\d+)\.(\d+)$")


def _git(*args, timeout=30):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=timeout, env=env)
    return r.returncode, (r.stdout + r.stderr).strip()


def _ver(tag):
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def current():
    """('v0.3.0', 'v0.3.0 + 4 newer changes') for this folder, or (None, 'not a git checkout')."""
    rc, base = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    if rc:
        return None, "not a git checkout"
    _, n = _git("rev-list", "--count", f"{base}..HEAD")
    return base, base + (f" + {n} newer changes" if n.isdigit() and int(n) else "")


def latest():
    """The newest release tag on GitHub like 'v0.4.0', or raises RuntimeError with a plain reason."""
    try:
        rc, out = _git("ls-remote", "--tags", "--refs", "origin", timeout=25)
    except subprocess.TimeoutExpired:
        raise RuntimeError("GitHub didn't answer in time.")
    if rc:
        raise RuntimeError(("Couldn't reach GitHub: " + out.splitlines()[-1]) if out else "Couldn't reach GitHub.")
    tags = [m for m in (TAG.match(line.split("\t")[-1]) for line in out.splitlines()) if m]
    if not tags:
        raise RuntimeError("No releases found on GitHub.")
    return "v%d.%d.%d" % max(tuple(int(g) for g in m.groups()) for m in tags)


def check():
    """(have, latest, newer) where newer is True when GitHub has a release past this one."""
    have, _ = current()
    if have is None:
        raise RuntimeError("This folder isn't a git checkout, so it can't update itself.")
    new = latest()
    return have, new, _ver(new) > _ver(have)


def update(tag):
    """Fast-forward to a release tag. Returns a message; raises RuntimeError if it can't do it safely."""
    _, dirty = _git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise RuntimeError("You have uncommitted changes here, so I didn't touch anything. Commit or stash them first.")
    rc, out = _git("fetch", "origin", "tag", tag, "--no-tags", timeout=60)
    if rc:
        raise RuntimeError("Couldn't download the release: " + out[-200:])
    rc, out = _git("merge", "--ff-only", tag)
    if rc:
        raise RuntimeError("This copy has its own commits that the release doesn't include, "
                           "so it can't fast-forward. Merge it by hand with git.")
    return f"Updated to {tag}."

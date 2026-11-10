"""Checks GitHub for a newer release (a v1.2.3 tag) and fast-forwards this folder to it.

Uses the git already set up here (the repo is public, so no login is needed); nothing is
downloaded outside git, and an update never overwrites changes you've made (it refuses instead)."""
import os
import re
import shutil
import subprocess
import tarfile
import tempfile

EXE = os.environ.get("DESKTOP_BUDDY_EXE")   # set when running from the one-file build (no git checkout)
REPO_URL = "https://github.com/Treeyagi/desktop-buddy.git"
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
    if EXE:   # the one-file build carries its version
        try:
            v = open(os.path.join(ROOT, "VERSION")).read().strip()
        except OSError:
            return None, "unknown version"
        m = re.match(r"v\d+\.\d+\.\d+", v)
        return (m.group(0), v) if m else (None, "unknown version")
    rc, base = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    if rc:
        return None, "not a git checkout"
    _, n = _git("rev-list", "--count", f"{base}..HEAD")
    return base, base + (f" + {n} newer changes" if n.isdigit() and int(n) else "")


def latest():
    """The newest release tag on GitHub like 'v0.4.0', or raises RuntimeError with a plain reason."""
    try:
        rc, out = _git("ls-remote", "--tags", "--refs", REPO_URL if EXE else "origin", timeout=25)
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
        raise RuntimeError("I can't tell which version this is, so it can't update itself.")
    new = latest()
    return have, new, _ver(new) > _ver(have)


def _update_exe(tag):
    """The one-file build: download the release's desktop-buddy.tar.gz and swap the file for the new one."""
    tmp = tempfile.mkdtemp(prefix="buddy-update-")
    try:
        archive = os.path.join(tmp, "desktop-buddy.tar.gz")
        url = f"https://github.com/Treeyagi/desktop-buddy/releases/download/{tag}/desktop-buddy.tar.gz"
        if shutil.which("curl"):   # the repo is public: no login needed
            argv = ["curl", "-fsSL", "-o", archive, url]
        elif shutil.which("gh"):
            argv = ["gh", "release", "download", tag, "--repo", "Treeyagi/desktop-buddy",
                    "--pattern", "desktop-buddy.tar.gz", "--dir", tmp, "--clobber"]
        else:
            raise RuntimeError("Updating needs curl (or the GitHub CLI). Run: sh tools/install-deps.sh")
        r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        if r.returncode or not os.path.exists(archive):
            raise RuntimeError("That release has no one-file download: " + (r.stderr.strip()[-150:] or tag))
        with tarfile.open(archive) as t:
            member = t.getmember("desktop-buddy")
            t.extract(member, tmp, filter="data") if hasattr(tarfile, "data_filter") else t.extract(member, tmp)
        new = os.path.join(tmp, "desktop-buddy")
        staged = EXE + ".new"
        shutil.copy2(new, staged)
        os.chmod(staged, 0o755)
        os.replace(staged, EXE)   # swaps the file in one step; the running copy keeps working
    except (OSError, KeyError, tarfile.TarError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"Couldn't update: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return f"Updated to {tag}."


def update(tag):
    """Fast-forward to a release tag. Returns a message; raises RuntimeError if it can't do it safely."""
    if EXE:
        return _update_exe(tag)
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

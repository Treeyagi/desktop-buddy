"""Keeps the Anthropic API key in the system keyring (KWallet on Plasma, reached
through the Secret Service with `secret-tool`), never in a plain file."""
import shutil
import subprocess

ATTRS = ["service", "desktop-buddy", "key", "anthropic-api-key"]


def available():
    return shutil.which("secret-tool") is not None


def get():
    if not available():
        return None
    out = subprocess.run(["secret-tool", "lookup", *ATTRS], capture_output=True, text=True)
    return out.stdout.strip() or None


def store(value):
    """Returns an error message, or None when the key was saved."""
    if not available():
        return "secret-tool isn't installed (it comes with libsecret)."
    out = subprocess.run(["secret-tool", "store", "--label", "Desktop Buddy: Anthropic API key", *ATTRS],
                         input=value, capture_output=True, text=True)
    return None if out.returncode == 0 else (out.stderr.strip() or "Couldn't save to the keyring.")


def clear():
    if available():
        subprocess.run(["secret-tool", "clear", *ATTRS], capture_output=True)

"""Speech to text, locally, with whisper.cpp's `whisper-cli` (pacman: whisper-cpp).

Models are the ggml files from the whisper.cpp project, kept in
~/.local/share/desktop-buddy/whisper/. Nothing you say leaves the computer here;
only the transcript goes on to Claude.
"""
import os
import re
import shutil
import subprocess

MODEL_DIR = os.path.expanduser("~/.local/share/desktop-buddy/whisper")
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{name}.bin"
MODELS = [  # (name, label)
    ("tiny.en", "Tiny (75 MB, fastest)"),
    ("base.en", "Base (142 MB, good default)"),
    ("small.en", "Small (466 MB, most accurate)"),
]
DEFAULT_MODEL = "base.en"


def whisper_cli():
    return shutil.which("whisper-cli")


def model_path(name):
    return os.path.join(MODEL_DIR, f"ggml-{name}.bin")


def have_model(name):
    path = model_path(name)
    return os.path.exists(path) and os.path.getsize(path) > 1_000_000


def problem(model=DEFAULT_MODEL):
    """Why transcription can't run yet, or None when it can."""
    if not whisper_cli():
        return "I can't hear yet: install whisper-cpp (sudo pacman -S whisper-cpp)."
    if not have_model(model):
        return "I can't hear yet: download a Whisper model in Settings > Claude > Voice."
    return None


def transcribe(wav, model=DEFAULT_MODEL, timeout=60):
    """Returns (text, error)."""
    why = problem(model)
    if why:
        return "", why
    cmd = [whisper_cli(), "-m", model_path(model), "-f", wav, "-l", "en", "-nt", "-np",
           "-t", str(max(2, min(8, (os.cpu_count() or 4) // 2)))]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "Transcribing took too long."
    if out.returncode != 0:
        return "", (out.stderr.strip().splitlines() or ["whisper-cli failed."])[-1][:200]
    text = " ".join(line.strip() for line in out.stdout.splitlines() if line.strip())
    text = re.sub(r"\[[A-Z _]+\]|\([^)]*\)", "", text).strip()  # [BLANK_AUDIO], (music) and the like
    return text, ""

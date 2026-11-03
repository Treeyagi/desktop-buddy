"""Ask Claude something and get the buddy's answer, in character.

Two ways in, picked in the settings window's Claude tab:
  claude-code  the Claude Code command (`claude -p`), signed in with your Claude plan.
               Runs with no tools and none of your Claude Code customizations.
  api          the Anthropic API through the official `anthropic` SDK
               (pip install --user --break-system-packages anthropic), using the key in your keyring
               (see keychain.py) or ANTHROPIC_API_KEY / an `ant auth login` profile.

The system prompt is personality.md plus the filled-in parts of who-i-am.md.
ask() blocks, so call it off the UI thread.
"""
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass

from brain import keychain

HERE = os.path.dirname(os.path.abspath(__file__))
WORKDIR = os.path.expanduser("~/.config/desktop-buddy")  # neutral folder: no project CLAUDE.md

MODELS = [
    ("claude-opus-5-5", "Claude Opus 5.5 (smartest, default)"),
    ("claude-sonnet-5-5", "Claude Sonnet 5.5 (faster)"),
    ("claude-haiku-5-5", "Claude Haiku 5.5 (fastest, cheapest)"),
]
DEFAULT_MODEL = "claude-opus-5-5"
# server-side refusal fallback ("default" routing) is available for these on the Claude API
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}


@dataclass
class Reply:
    text: str = ""
    error: str = ""
    seconds: float = 0.0
    backend: str = ""
    model: str = ""


def _read(name):
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def who_i_am():
    """The sections of who-i-am.md the user actually filled in."""
    text = _read("who-i-am.md")
    if "## " not in text:
        return ""
    out = []
    for section in text.split("\n## ")[1:]:
        title, _, body = section.partition("\n")
        lines = [ln for ln in body.strip().splitlines() if ln.strip() and not ln.strip().startswith("(fill in")]
        if lines:
            out.append(f"{title.strip()}:\n" + "\n".join(lines))
    return "\n\n".join(out)


def system_prompt():
    prompt = _read("personality.md").strip()
    me = who_i_am()
    if me:
        prompt += "\n\nAbout the user (you are a cartoon of them):\n\n" + me
    return prompt


def claude_cli():
    return shutil.which("claude")


def sdk_installed():
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def ask(question, backend="claude-code", model=DEFAULT_MODEL, timeout=120):
    start = time.monotonic()
    fn = _ask_api if backend == "api" else _ask_cli
    reply = fn(question.strip(), model, timeout)
    reply.seconds = time.monotonic() - start
    reply.backend, reply.model = backend, model
    return reply


def _ask_cli(question, model, timeout):
    exe = claude_cli()
    if not exe:
        return Reply(error="Claude Code isn't installed (no `claude` command found).")
    os.makedirs(WORKDIR, exist_ok=True)
    cmd = [exe, "-p", "--system-prompt", system_prompt(), "--model", model, "--tools", "",
           "--safe-mode", "--no-session-persistence", "--strict-mcp-config", "--output-format", "json"]
    try:
        out = subprocess.run(cmd, cwd=WORKDIR, input=question, capture_output=True, text=True,
                             timeout=timeout)
    except subprocess.TimeoutExpired:
        return Reply(error=f"Claude Code didn't answer within {timeout} seconds.")
    try:
        data = json.loads(out.stdout)
    except ValueError:
        msg = (out.stderr or out.stdout).strip()
        return Reply(error=msg[:400] or "Claude Code gave no answer.")
    if data.get("is_error"):
        return Reply(error=str(data.get("result") or data.get("subtype") or "Claude Code reported an error."))
    return Reply(text=str(data.get("result", "")).strip())


def _ask_api(question, model, timeout):
    try:
        import anthropic
    except ImportError:
        return Reply(error="The Anthropic SDK isn't installed. Install it with: pip install --user --break-system-packages anthropic")
    key = keychain.get()
    try:
        client = anthropic.Anthropic(api_key=key, timeout=timeout) if key else anthropic.Anthropic(timeout=timeout)
    except anthropic.AnthropicError:
        return Reply(error="No API key: save one in the Claude tab, or set ANTHROPIC_API_KEY.")
    params = dict(
        model=model,
        max_tokens=16000,
        system=system_prompt(),
        messages=[{"role": "user", "content": question}],
        output_config={"effort": "low"},  # short spoken chat replies
    )
    try:
        if model in FALLBACK_MODELS:  # a policy decline gets re-run on a fallback model in the same call
            response = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"],
                                                   fallbacks="default", **params)
        else:
            response = client.messages.create(**params)
    except anthropic.AuthenticationError:
        return Reply(error="The API key was rejected. Check it in the Claude tab.")
    except anthropic.PermissionDeniedError:
        return Reply(error="This API key isn't allowed to use that model.")
    except anthropic.NotFoundError:
        return Reply(error="That model isn't available to this API key.")
    except anthropic.RateLimitError:
        return Reply(error="Rate limited. Try again in a minute.")
    except anthropic.APIStatusError as e:
        return Reply(error=f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        return Reply(error="Couldn't reach the Anthropic API. Check your internet connection.")
    if response.stop_reason == "refusal":
        return Reply(error="Claude declined to answer that one.")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return Reply(text=text)

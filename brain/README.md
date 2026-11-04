# brain

Where Claude gets called, and where the personality lives.

- **Inputs:** transcripts from `voice-in/` (push-to-talk), a screenshot, only when the "Look at my screen" hotkey is used
- **Outputs:** reply text for `voice-out/` and `character/`. For now it's shown in the settings window's "Try him" box.
- **Still planned:** a mood tag on replies, the multi-pass hyperfocus loop (try, check, search, deliver).

## Files
- `personality.md`: the system prompt. Snarky raw philosopher, always lands on a solution, never cruel to the helpless, no cop-outs, sincere about faith and family without preaching, and short spoken answers. Edit it freely.
- `who-i-am.md`: you fill this in (name, family, faith, passions, sayings, pet peeves, how you talk). Only sections you've filled in get sent; anything still marked "(fill in)" is skipped.
- `client.py`: `ask(question, backend, model)` returns a `Reply` (text or error, seconds taken). It blocks, so call it off the UI thread.
- `keychain.py`: keeps the API key in the system keyring (KWallet on Plasma, through `secret-tool`), never in a file.

## Two ways to reach Claude (Claude tab in settings)
- **Claude Code** (default): runs `claude -p` signed in with your Claude plan, so it counts against your plan's limits. It runs in `~/.config/desktop-buddy` with no tools, `--safe-mode` (none of your Claude Code plugins, hooks, MCP servers or CLAUDE.md files) and no saved session. Nothing to install. A short answer took about 3 s on Haiku and about 7 s on Opus in testing. If you're unsure whether your plan covers this kind of use, check your plan's terms.
- **API key:** the official `anthropic` SDK. Install it with `pip install --user --break-system-packages anthropic` (or put it in a virtual environment). The key is pasted into the Claude tab and saved to KWallet. Otherwise `ANTHROPIC_API_KEY` or an `ant auth login` profile also works. Requests use `effort: "low"` (short chat replies). On Opus 5.5 and Sonnet 5.5 they also turn on the server-side refusal fallback (`fallbacks: "default"`), so a policy decline gets retried on another model in the same call. A refusal is reported instead of failing silently. For a spending cap, set a monthly limit on the key in the Anthropic Console.

Models: Claude Opus 5.5 (default, smartest), Claude Sonnet 5.5 (faster), Claude Haiku 5.5 (fastest, cheapest). For snappy voice replies later, Sonnet or Haiku may feel better.

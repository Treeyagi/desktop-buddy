# brain notes

Reference for this folder: [README.md](README.md) — the two backends, the models, the files, the keyring.

## Do not edit these two files

`personality.md` and `who-i-am.md` are **the user's own words** about his family, faith, passions and how he
talks. They're the product, not configuration. Don't rewrite them, tidy the prose or fill in blanks — only
the user edits those. Sections still marked "(fill in)" are skipped on purpose.

## While working here

- **The API key goes in the system keyring only** (`keychain.py`, KWallet via `secret-tool`) — never in a
  file, never in the repo. **This repo is public.**
- The default backend is Claude Code with `--safe-mode`, no tools and no saved session, run in
  `~/.config/desktop-buddy`. That isolation is deliberate: it stops the buddy inheriting the user's own
  Claude Code plugins, hooks or `CLAUDE.md` files. Don't remove it.
- `client.ask()` **blocks** — call it off the UI thread. `session.py` keeps one warm `claude` process
  (restarts after 10 questions, 20 idle minutes, or a personality/model change).
- A screenshot is sent **only** on the "Look at my screen" hotkey. That's the one costly, privacy-relevant
  path ([why](../docs/explanation/privacy-cost-and-licensing.md)).
- Keep replies short — two sentences, set in `personality.md`. It's what keeps him snappy and the speech brief.

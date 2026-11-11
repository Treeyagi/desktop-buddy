# Desktop Buddy docs

These docs follow [Diataxis](https://diataxis.fr): four kinds of page, each answering one kind of question.

**Reference lives in the per-module `README.md` files**, not in here. They're detailed and kept current, so
these pages deliberately don't repeat them — [reference/module-index.md](reference/module-index.md) is just a
map to them.

| Folder | Answers | Pages |
|---|---|---|
| `tutorials/` | "Teach me by doing" | *(empty — the module READMEs plus `ROADMAP.md` cover getting started)* |
| `how-to/` | "How do I do this specific job?" | [check-your-work](how-to/check-your-work.md), [add-things](how-to/add-things.md), [release](how-to/release.md) |
| `reference/` | "What exactly is X?" | [module-index](reference/module-index.md) → the real reference is each module's README |
| `explanation/` | "Why does it work this way?" | [privacy-cost-and-licensing](explanation/privacy-cost-and-licensing.md) |

How it all fits together and the decisions behind it: [../ARCHITECTURE.md](../ARCHITECTURE.md).

**[NOTES.md](NOTES.md)** is the original brainstorm from before the app was built — the personality, the
signature behaviours, the idea bank. It's kept exactly as written, so its "Status: planning only" line is
historical, not current. Treat it as the vision document; `ROADMAP.md` is the live plan.

There are nested `CLAUDE.md` files in `character/`, `brain/`, `voice-in/`, `voice-out/`,
`desktop-awareness/` and `settings/`. They load automatically when working in those folders.

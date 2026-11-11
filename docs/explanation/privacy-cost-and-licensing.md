# Why the mic, the screen, the key and the melodies have rules

Desktop Buddy sits on the user's desktop with a microphone, the ability to screenshot, and a paid API key.
It's also a **public repo**. Each rule below closes a specific way that could go wrong.

## The microphone

**Never leave the mic recording.** Recordings are deleted after use, and `tools/shutdown.py` deletes any that
are left over.

Push-to-talk is a deliberate design: he records while a key is held and not otherwise. An always-listening
buddy would be a more convenient product and a much worse thing to have running on someone's desktop. Don't
quietly widen it — "just listen for a wake word" is a different app with different consent.

## The screen

**A screenshot is taken only when the "Look at my screen" hotkey is pressed.** That's the single moment a
picture of the user's desktop leaves the machine, and it's also the only time that costs usage money beyond a
plain question.

Everything else he reacts to — window titles and positions, icon positions, the cursor — is read locally
through Plasma's config and a KWin script. He can stand next to a browser window and do a reading animation
without anything being sent anywhere. Keep new awareness features on that side of the line.

`tools/shutdown.py` deletes leftover screenshots for the same reason it deletes audio.

## The KWin script and the user's shortcuts

**KWin scripts must be unloaded when done.** A script left loaded keeps running inside the user's window
manager after the buddy is gone, which is both a resource leak and a surprise.

**Don't change the user's KDE shortcuts beyond push-to-talk.** Their keyboard is theirs; the buddy gets the
one binding he was invited to take.

## The API key

`brain/keychain.py` keeps the key in the system keyring — KWallet on Plasma, through `secret-tool` — and
**never in a file**. Not in the repo, not in `~/.config`, not in an environment file that could get committed.

This repo is public, so a key in a file is a key on the internet. For a spending cap, the user sets a monthly
limit on the key in the Anthropic Console.

The default backend avoids the key entirely: Claude Code signed in with the user's own plan, run with
`--safe-mode`, no tools and no saved session, in `~/.config/desktop-buddy`. That isolation also stops the
buddy inheriting the user's Claude Code plugins, hooks or `CLAUDE.md` files — which would otherwise leak this
project's own instructions into his personality.

## The melodies and the vending machine

His hums are **six two-bar melodies generated from scratch at runtime** (124 BPM, A minor pentatonic, soft
vibrato) and cached in `~/.cache/desktop-buddy/`. No real songs, no samples. They play at 12% volume, never
during a call.

The vending machine in the signature random event is an **original look-alike** — generic card machine,
original logo and card art.

Both exist so this can be a public repo someone else can clone without a licensing problem. Anything new that
plays music or depicts something recognisable needs the same treatment.

## The personality files are not yours to edit

`brain/personality.md` and `brain/who-i-am.md` are the user's own words about his own family, faith and
passions. They're the product, not configuration. Don't rewrite, tidy or "improve" them — only the user edits
those files.

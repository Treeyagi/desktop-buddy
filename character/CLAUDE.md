# character notes

Reference for this folder: [README.md](README.md) — the look, every file, every action and scene, and the
sprite pack. Read it before editing here.

## He has two looks — check both

- `rig.py` draws him from code (body, face, hat, shoes); `moves.py` holds shared poses.
- `sprite.py` is the alternative look (Settings → Character): the pack in `sprites/treeyagi/`, 29 animations
  in eight directions, timings and anchors in `anims.json`, mapped by `anim_for()`.

A behaviour change can look right in one look and wrong in the other. Verify with
`python3 preview.py out.png --actions <name>`.

## While working here

- **Don't read `rig.py` or `scenes.py` unless the task is about them** — they're large and they're drawing
  code. `grep -n "def "` and read the range you need.
- Behaviour lives in `behavior.py` (`Buddy.pick_next`, `_<name>()` methods returning a `Pose`), not in
  either renderer. New action → the recipe in [../docs/how-to/add-things.md](../docs/how-to/add-things.md).
- Need something from another module? **Add a bus topic, not an import**
  (topics are listed in [../core/README.md](../core/README.md)).
- Anything new that depicts something recognisable must be an original look-alike, like the vending machine
  ([why](../docs/explanation/privacy-cost-and-licensing.md)).

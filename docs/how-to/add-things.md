# How to add things

Three recipes. Each one touches a known set of places — miss one and the thing half-works.

## A new action

1. Add `"name": (weight, (min_s, max_s))` to `ACTIONS` in `character/behavior.py`.
2. Add a `_name(self, dt)` method returning a `Pose` (and optionally `_start_name`).
3. Add a row to `BEHAVIORS` in `settings/tabs/common.py`, so it can be turned off.
4. Check it with `python3 character/preview.py out.png --actions name`, in **both** looks if it's visual.

## A new setting

Four places, all required:

1. `DEFAULTS` in `settings/store.py`.
2. Apply it in `Controller.apply` in `overlay/main.py` — this is what makes it take effect live.
3. The widget in its tab file (`settings/tabs/<tab>.py`), plus a line in that tab's `_sync_<tab>()`.
4. Document it in `settings/README.md`.

Check with `python3 tools/render_tab.py <tab> out.png`.

## A new bus topic

1. Publish with `bus.publish(topic, payload)`; subscribe where it's consumed.
2. **Add a row to the topic table in `core/README.md`** — payload, which module sends it, who uses it.

That table is the contract between modules. A topic that isn't in it is invisible to the next person.

## The general rule

When a module needs something from another module, **add a bus topic rather than an import**. Modules talk
only through the bus; that's what keeps each folder workable on its own.

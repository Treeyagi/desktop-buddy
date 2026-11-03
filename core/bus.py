"""Tiny in-process event bus. Modules publish and subscribe by topic name, so
none of them needs to import the others. Topics are listed in core/README.md."""
from collections import defaultdict


class Bus:
    def __init__(self):
        self._subs = defaultdict(list)

    def subscribe(self, topic, fn):
        self._subs[topic].append(fn)

    def publish(self, topic, payload=None):
        for fn in list(self._subs[topic]):
            fn(payload)

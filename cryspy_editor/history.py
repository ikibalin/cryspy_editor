"""History of the rcif object: its text before each change, without Qt.

The main window keeps the last N_HISTORY states, so that the user can go
back when a refinement or an edit went wrong. The history lives in memory
for the session of the program.
"""
import time
from typing import List, NamedTuple

N_HISTORY = 10


class HistoryEntry(NamedTuple):
    time: float
    label: str
    text: str

    def title(self) -> str:
        return f"{time.strftime('%H:%M:%S', time.localtime(self.time))}  before {self.label}"


class RcifHistory:
    """The last states of the rcif object, the newest one last."""

    def __init__(self, n_max: int = N_HISTORY):
        self.n_max = n_max
        self.entries: List[HistoryEntry] = []

    def push(self, label: str, text: str) -> bool:
        """Keep the state before the change `label`. A state equal to the
        newest kept one is not added again: that entry takes the new label
        (the last action tried on it). Returns True if added."""
        if self.entries and self.entries[-1].text == text:
            self.entries[-1] = HistoryEntry(time.time(), label, text)
            return False
        self.entries.append(HistoryEntry(time.time(), label, text))
        del self.entries[:-self.n_max]
        return True

    def clear(self):
        self.entries = []

    def __len__(self) -> int:
        return len(self.entries)

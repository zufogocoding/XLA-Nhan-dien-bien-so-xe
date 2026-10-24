"""Bounded temporal voting for a single plate/track; ties remain unresolved."""

from collections import Counter, deque


class VideoVoting:
    def __init__(self, window_size: int = 20):
        if not 10 <= window_size <= 30:
            raise ValueError("window_size must be between 10 and 30")
        self.values = deque(maxlen=window_size)

    def update(self, text: str | None) -> dict:
        # Empty frames advance the window too, so stale detections expire.
        self.values.append(text or None)
        counts = Counter(value for value in self.values if value)
        if not counts:
            return {"plate_text": None, "votes": 0, "observations": len(self.values), "vote_ratio": 0.0}
        ranked = counts.most_common()
        tied = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
        return {"plate_text": None if tied else ranked[0][0], "votes": ranked[0][1], "observations": len(self.values), "vote_ratio": ranked[0][1] / len(self.values)}

    def reset(self) -> None:
        self.values.clear()

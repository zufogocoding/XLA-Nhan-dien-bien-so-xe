"""Persisted local recognition record, including unsuccessful processing results."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class PlateRecord:
    plate_text: str | None = None
    confidence: float | None = None
    image_path: str | None = None
    crop_path: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    vehicle_type: str = "unknown"
    line_type: str | None = None
    province: str | None = None
    raw_text: str | None = None
    model_version: str | None = None
    is_valid: bool = False
    status: str = "pending"
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

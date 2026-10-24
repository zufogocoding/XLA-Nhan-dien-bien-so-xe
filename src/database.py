"""Parameterized SQLite CRUD for the user-selected local development target."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from .models import PlateRecord

FIELDS = ("plate_text", "confidence", "image_path", "crop_path", "timestamp", "vehicle_type", "line_type", "province", "raw_text", "model_version", "is_valid", "status", "error", "metadata")


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_text TEXT, confidence REAL, image_path TEXT, crop_path TEXT,
                timestamp TEXT NOT NULL, vehicle_type TEXT, line_type TEXT,
                province TEXT, raw_text TEXT, model_version TEXT,
                is_valid INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
                error TEXT, metadata TEXT NOT NULL DEFAULT '{}'
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_plates_timestamp ON plates(timestamp)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_plates_text ON plates(plate_text)")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        result["is_valid"] = bool(result["is_valid"])
        return result

    def create(self, record: PlateRecord) -> dict:
        values = record.to_dict()
        values["metadata"] = json.dumps(values["metadata"], ensure_ascii=False)
        values["is_valid"] = int(values["is_valid"])
        with self.connection() as db:
            cursor = db.execute(f"INSERT INTO plates ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})", [values[key] for key in FIELDS])
            return self.decode(db.execute("SELECT * FROM plates WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def get(self, record_id: int) -> dict | None:
        with self.connection() as db:
            return self.decode(db.execute("SELECT * FROM plates WHERE id = ?", (record_id,)).fetchone())

    def list(self, *, limit: int = 50, offset: int = 0, query: str = "") -> dict:
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("limit must be 1..200 and offset nonnegative")
        where, params = (" WHERE plate_text LIKE ?", [f"%{query}%"]) if query else ("", [])
        with self.connection() as db:
            total = db.execute("SELECT COUNT(*) FROM plates" + where, params).fetchone()[0]
            rows = db.execute("SELECT * FROM plates" + where + " ORDER BY id DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        return {"items": [self.decode(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def update(self, record_id: int, changes: dict) -> dict | None:
        if not changes or not set(changes) <= set(FIELDS):
            raise ValueError("update contains unsupported fields")
        values = dict(changes)
        if "metadata" in values:
            values["metadata"] = json.dumps(values["metadata"], ensure_ascii=False)
        if "is_valid" in values:
            values["is_valid"] = int(values["is_valid"])
        with self.connection() as db:
            db.execute("UPDATE plates SET " + ",".join(f"{key} = ?" for key in values) + " WHERE id = ?", [*values.values(), record_id])
            return self.decode(db.execute("SELECT * FROM plates WHERE id = ?", (record_id,)).fetchone())

    def delete(self, record_id: int) -> bool:
        with self.connection() as db:
            return db.execute("DELETE FROM plates WHERE id = ?", (record_id,)).rowcount > 0

    def stats(self) -> dict:
        with self.connection() as db:
            total, valid = db.execute("SELECT COUNT(*), COALESCE(SUM(is_valid),0) FROM plates").fetchone()
            statuses = {row[0]: row[1] for row in db.execute("SELECT status, COUNT(*) FROM plates GROUP BY status")}
            provinces = {row[0]: row[1] for row in db.execute("SELECT province, COUNT(*) FROM plates WHERE province IS NOT NULL GROUP BY province ORDER BY COUNT(*) DESC")}
        return {"total": total, "valid": valid, "by_status": statuses, "by_province": provinces}

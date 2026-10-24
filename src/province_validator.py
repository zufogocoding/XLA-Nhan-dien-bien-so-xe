"""Current registration-code lookup from a sourced CSV, including central code 80."""

import csv
from pathlib import Path


class ProvinceRegistry:
    def __init__(self, csv_path: str | Path | None = None):
        path = Path(csv_path) if csv_path else Path(__file__).resolve().parents[1] / "data/provinces.csv"
        self.entries = {}
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                for code in row["codes"].split(";"):
                    if len(code) != 2 or not code.isascii() or not code.isdigit() or code in self.entries:
                        raise ValueError(f"invalid or duplicated province code: {code}")
                    self.entries[code] = dict(row)

    def lookup(self, code: str) -> dict | None:
        entry = self.entries.get(code)
        return dict(entry) if entry else None

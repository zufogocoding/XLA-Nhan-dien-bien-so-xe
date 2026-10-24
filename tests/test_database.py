from src.database import Database
from src.models import PlateRecord


def test_crud_persists_success_and_failure_without_sql_interpolation(tmp_path):
    db = Database(tmp_path / "plates.sqlite3")
    first = db.create(PlateRecord(plate_text="51F-123.45", is_valid=True, status="recognized", metadata={"bbox":[1,2,3,4]}))
    second = db.create(PlateRecord(status="no_plate"))
    assert db.get(first["id"])["metadata"] == {"bbox":[1,2,3,4]}
    assert db.list()["total"] == 2
    assert db.stats()["valid"] == 1
    assert db.list(query="' OR 1=1 --")["total"] == 0
    assert db.update(first["id"],{"plate_text":"29A-1234"})["plate_text"] == "29A-1234"
    assert db.delete(second["id"]) and not db.delete(second["id"])

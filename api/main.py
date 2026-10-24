"""Serve the HTML/JS demo and WP1–WP4 CRUD endpoints on localhost."""

from pathlib import Path
import os
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.models import PlateRecord
from src.pipeline_wp4 import postprocess
from src.service import RecognitionService

ROOT = Path(__file__).resolve().parents[1]


class ManualPlate(BaseModel):
    plate_text: str = Field(min_length=1, max_length=30)
    vehicle_type: str = "unknown"


def create_app(runtime: Path | None = None, model_dir: Path | None = None) -> FastAPI:
    service = RecognitionService(runtime or Path(os.environ.get("ALPR_RUNTIME_DIR", ROOT / "outputs/runtime")), model_dir)
    app = FastAPI(title="Nhận diện biển số xe", version="0.1.0")
    app.state.service = service

    def hint(value: str):
        if value not in ("unknown", "car", "motorcycle"):
            raise HTTPException(422, "vehicle_type must be unknown, car or motorcycle")
        return value

    async def save_upload(file: UploadFile, kind: str) -> Path:
        suffix = Path(file.filename or "").suffix.lower()
        allowed = {".jpg", ".jpeg", ".png", ".bmp", ".webp"} if kind == "image" else {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        if suffix not in allowed:
            raise HTTPException(415, f"unsupported {kind} extension")
        path = service.public / "uploads" / (uuid.uuid4().hex + suffix)
        total = 0
        maximum = int(os.environ.get("ALPR_MAX_UPLOAD_MB", "256")) * 1024 * 1024
        try:
            with path.open("xb") as stream:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > maximum:
                        raise HTTPException(413, "file exceeds configured upload limit")
                    stream.write(chunk)
            if total == 0:
                raise HTTPException(400, "empty upload")
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        return path

    @app.get("/api/health")
    def health():
        return {"status": "ok", **service.readiness()}

    @app.post("/api/upload/image")
    async def upload_image(file: UploadFile = File(...), vehicle_type: str = Form("unknown")):
        hint(vehicle_type)
        path = await save_upload(file, "image")
        try:
            return await run_in_threadpool(service.process_image, path, vehicle_type=vehicle_type)
        except ValueError as exc:
            path.unlink(missing_ok=True)
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/upload/video")
    async def upload_video(file: UploadFile = File(...), vehicle_type: str = Form("unknown"), stride: int = Form(5, ge=1, le=60)):
        hint(vehicle_type)
        path = await save_upload(file, "video")
        try:
            return await run_in_threadpool(service.process_video, path, stride=stride, vehicle_type=vehicle_type)
        except ValueError as exc:
            path.unlink(missing_ok=True)
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/plates")
    def list_plates(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), q: str = Query("", max_length=30)):
        result = service.database.list(limit=limit, offset=offset, query=q)
        result["items"] = [service.with_urls(record) for record in result["items"]]
        return result

    @app.get("/api/plates/{record_id}")
    def get_plate(record_id: int):
        record = service.database.get(record_id)
        if record is None:
            raise HTTPException(404, "record not found")
        return service.with_urls(record)

    @app.post("/api/plates", status_code=201)
    def create_plate(payload: ManualPlate):
        hint(payload.vehicle_type)
        result = postprocess(payload.plate_text, [], vehicle_type=payload.vehicle_type)
        record = PlateRecord(plate_text=result["plate_text"], raw_text=payload.plate_text, vehicle_type=result["vehicle_type"], province=result["province"], is_valid=result["is_valid"], status="manual", model_version="manual", metadata={"postprocessing": result})
        return service.with_urls(service.database.create(record))

    @app.patch("/api/plates/{record_id}")
    def edit_plate(record_id: int, payload: ManualPlate):
        hint(payload.vehicle_type)
        existing = service.database.get(record_id)
        if existing is None:
            raise HTTPException(404, "record not found")
        result = postprocess(payload.plate_text, [], vehicle_type=payload.vehicle_type)
        metadata = dict(existing["metadata"])
        metadata.setdefault("original_model_confidence", existing["confidence"])
        metadata.update({"manual_review": True, "postprocessing": result})
        return service.with_urls(service.database.update(record_id, {"plate_text": result["plate_text"], "confidence": None, "vehicle_type": result["vehicle_type"], "province": result["province"], "is_valid": result["is_valid"], "status": "manual", "metadata": metadata}))

    @app.delete("/api/plates/{record_id}", status_code=204)
    def delete_plate(record_id: int):
        if not service.database.delete(record_id):
            raise HTTPException(404, "record not found")

    @app.get("/api/stats")
    def statistics():
        return service.database.stats()

    app.mount("/files", StaticFiles(directory=service.public), name="files")
    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "web/index.html")

    return app


app = create_app()

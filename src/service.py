"""Local WP1–WP4 integration and persistence for image/video requests."""

import json
from pathlib import Path
from time import perf_counter
import uuid

import cv2
import numpy as np

from .character_classifier import CharacterClassifier, ModelNotReadyError
from .database import Database
from .detection import _iou
from .models import PlateRecord
from .pipeline_wp1 import detect_plate_image
from .recognition_selection import select_plate_for_recognition
from .pipeline_wp2 import segment_plate, SEGMENTATION_VERSION
from .pipeline_wp3 import recognize_characters
from .pipeline_wp4 import postprocess
from .video_voting import VideoVoting


class RecognitionService:
    def __init__(self, runtime: Path, model_dir: Path | None = None):
        self.runtime = Path(runtime)
        self.public = self.runtime / "public"
        for subdirectory in ("uploads", "crops", "characters", "processing"):
            (self.public / subdirectory).mkdir(parents=True, exist_ok=True)
        self.database = Database(self.runtime / "plates.sqlite3")
        self.model_dir = model_dir or Path(__file__).resolve().parents[1] / "models"
        self._classifier = None
        self._model_key = None

    def classifier(self) -> CharacterClassifier:
        manifest = self.model_dir / "ocr_manifest.json"
        filename = json.loads(manifest.read_text(encoding="utf-8"))["artifact"] if manifest.exists() else "svm_hog.pkl"
        # Only artifacts within the configured model directory may be selected.
        path = (self.model_dir / filename).resolve()
        if path.parent != self.model_dir.resolve():
            raise ValueError("OCR manifest artifact must be inside models directory")
        key = (str(path), path.stat().st_mtime_ns if path.exists() else None)
        if key != self._model_key:
            self._classifier = CharacterClassifier(path)
            self._model_key = key
        return self._classifier

    def readiness(self) -> dict:
        try:
            bundle = self.classifier().load()
            return {"ocr_ready": True, "model_version": bundle.get("model_version"), "character_size": 32, "segmentation_version": SEGMENTATION_VERSION}
        except (ModelNotReadyError, ValueError) as exc:
            return {"ocr_ready": False, "detail": str(exc), "character_size": 32, "segmentation_version": SEGMENTATION_VERSION}

    @staticmethod
    def with_urls(record: dict) -> dict:
        result = dict(record)
        for field in ("image_path", "crop_path"):
            result[field.replace("_path", "_url")] = "/files/" + record[field] if record.get(field) else None
        return result

    def process_frame(self, image: np.ndarray, source: str, *, vehicle_type: str = "unknown", extra: dict | None = None) -> dict:
        start = perf_counter()
        record = PlateRecord(image_path=source, metadata=dict(extra or {}))
        try:
            classifier=self.classifier()
            detection = select_plate_for_recognition(image,classifier) if classifier.model_path.is_file() else detect_plate_image(image)
            if detection is None:
                record.status = "no_plate"
            else:
                token = uuid.uuid4().hex
                crop = Path("crops") / f"{token}.png"
                cv2.imencode(".png", detection["plate_normalized"])[1].tofile(self.public / crop)
                record.crop_path = crop.as_posix()
                record.metadata.update({key: detection[key] for key in ("bbox", "angle", "confidence")})
                record.metadata["detection_score"] = record.metadata.pop("confidence")
                segmentation = detection.get('segmentation') or segment_plate(detection["plate_normalized"])
                record.line_type = segmentation["line_type"]
                record.metadata["positions"] = segmentation["positions"]
                record.metadata["num_chars"] = segmentation["num_chars"]
                record.metadata["segmentation_version"] = segmentation["algorithm_version"]
                record.metadata["line_method"] = segmentation["line_method"]
                record.metadata['threshold_method']=segmentation['threshold_method']
                record.metadata['frame_cleanup']=segmentation['frame_cleanup']
                record.metadata['detection_source']=detection.get('source')
                record.metadata['candidate_diagnostics']=detection.get('candidate_diagnostics',[])
                gray=cv2.cvtColor(detection['plate_normalized'],cv2.COLOR_BGR2GRAY)
                boxes=detection['plate_normalized'].copy()
                for index,(x,y,width,height) in enumerate(segmentation['positions']):
                    cv2.rectangle(boxes,(x,y),(x+width-1,y+height-1),(20,180,60),1)
                    cv2.putText(boxes,str(index+1),(x,max(9,y)),cv2.FONT_HERSHEY_SIMPLEX,.35,(20,120,20),1)
                record.metadata['processing_images']=[]
                for name,label,array in (('gray','Ảnh xám',gray),('binary','Ảnh nhị phân được chọn',segmentation['binary']),('boxes','Thứ tự và vùng ký tự',boxes)):
                    path=Path('processing')/f'{token}_{name}.png'
                    cv2.imencode('.png',array)[1].tofile(self.public/path)
                    record.metadata['processing_images'].append({'label':label,'url':'/files/'+path.as_posix()})
                record.metadata["character_urls"] = []
                for index, character in enumerate(segmentation["characters"]):
                    path = Path("characters") / f"{token}_{index}.png"
                    cv2.imencode(".png", character)[1].tofile(self.public / path)
                    record.metadata["character_urls"].append("/files/" + path.as_posix())
                if not segmentation["characters"]:
                    record.status = "segmentation_empty"
                else:
                    classifier = self.classifier()
                    ocr = detection.get('ocr') or recognize_characters(segmentation["characters"], classifier)
                    result = postprocess(ocr["raw_text"], ocr["confidences"], vehicle_type=vehicle_type)
                    record.plate_text = result["plate_text"]
                    record.raw_text = ocr["raw_text"]
                    record.confidence = result["confidence"]
                    record.is_valid = result["is_valid"]
                    record.province = result["province"]
                    record.vehicle_type = result["vehicle_type"]
                    record.model_version = classifier.load().get("model_version")
                    quality_ok = bool(ocr['confidences'] and min(ocr['confidences']) >= .35 and np.mean(ocr['confidences']) >= .8)
                    record.status = "recognized" if result["is_valid"] and quality_ok else "needs_review"
                    record.metadata['ocr_requires_review']=not quality_ok
                    record.metadata.update({"ocr": ocr, "postprocessing": result})
        except ModelNotReadyError as exc:
            record.status, record.error = "ocr_unavailable", str(exc)
        except (ValueError, cv2.error) as exc:
            record.status, record.error = "processing_error", str(exc)
        record.metadata["elapsed_ms"] = (perf_counter() - start) * 1000
        return self.with_urls(self.database.create(record))

    def process_image(self, path: Path, *, vehicle_type: str = "unknown") -> dict:
        image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("uploaded file is not a readable image")
        source = path.relative_to(self.public).as_posix()
        return self.process_frame(image, source, vehicle_type=vehicle_type)

    def process_video(self, path: Path, *, stride: int = 5, vehicle_type: str = "unknown") -> dict:
        if not 1 <= stride <= 60:
            raise ValueError("stride must be between 1 and 60")
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise ValueError("uploaded video cannot be opened")
        source = path.relative_to(self.public).as_posix()
        voting = VideoVoting(20)
        previous_box = None
        frame_index, processed, detections = 0, 0, 0
        records = []
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            while True:
                ok, image = capture.read()
                if not ok:
                    break
                if frame_index % stride == 0:
                    record = self.process_frame(image, source, vehicle_type=vehicle_type, extra={"frame_index": frame_index, "video_seconds": frame_index / fps if fps > 0 else None})
                    current_box = record["metadata"].get("bbox")
                    if current_box and previous_box and _iou(current_box, previous_box) < 0.2:
                        voting.reset()
                    vote = voting.update(record["plate_text"] if record["is_valid"] else None)
                    record["metadata"]["temporal_vote"] = vote
                    self.database.update(record["id"], {"metadata": record["metadata"]})
                    previous_box = current_box
                    processed += 1
                    detections += current_box is not None
                    # Bound the response; every processed frame stays in SQLite.
                    records.append(record)
                    records = records[-50:]
                frame_index += 1
        finally:
            capture.release()
        if frame_index == 0:
            raise ValueError("video contains no readable frames")
        return {"frames_read": frame_index, "frames_processed": processed, "detections": detections, "stride": stride, "items": records, "source_url": "/files/" + source, "voting_scope": "single best plate per sampled frame; spatial reset; no multi-object tracker"}

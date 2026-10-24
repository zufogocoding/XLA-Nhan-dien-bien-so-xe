import cv2
import numpy as np
from fastapi.testclient import TestClient

from api.main import create_app


def test_local_api_upload_crud_and_static_frontend(tmp_path):
    with TestClient(create_app(tmp_path / "runtime", tmp_path / "empty-models")) as client:
        assert client.get("/").status_code == 200
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/api/health").json()["ocr_ready"] is False
        content = cv2.imencode(".png", np.full((80,120,3),255,np.uint8))[1].tobytes()
        response = client.post("/api/upload/image", files={"file":("empty.png",content,"image/png")})
        assert response.status_code == 200
        record = response.json()
        assert record["status"] == "no_plate"
        assert client.get(record["image_url"]).status_code == 200
        assert client.get("/api/plates").json()["total"] == 1
        created = client.post("/api/plates",json={"plate_text":"51F12345","vehicle_type":"car"})
        assert created.status_code == 201
        key = created.json()["id"]
        edited = client.patch(f"/api/plates/{key}",json={"plate_text":"29A1234","vehicle_type":"car"})
        assert edited.json()["plate_text"] == "29A-1234"
        assert client.get("/api/stats").json()["total"] == 2
        assert client.delete(f"/api/plates/{key}").status_code == 204
        assert client.get(f"/api/plates/{key}").status_code == 404
        assert client.post("/api/upload/image",files={"file":("bad.png",b"not an image","image/png")}).status_code == 400
        assert client.post("/api/upload/image",files={"file":("bad.exe",b"x","application/octet-stream")}).status_code == 415

"""So'rov tanasi chegarasi (core/body_limit.py)."""

from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.body_limit import BodySizeLimitMiddleware

LIMIT = 1000


class Body(BaseModel):
    data: str


calls: list[str] = []

app = FastAPI()
app.add_middleware(
    BodySizeLimitMiddleware, default_limit=LIMIT, path_limits={"/big/": LIMIT * 10}
)


@app.post("/json")
def json_endpoint(body: Body):
    calls.append("json")
    return {"n": len(body.data)}


@app.post("/big/json")
def big_json_endpoint(body: Body):
    return {"n": len(body.data)}


@app.post("/upload")
def upload_endpoint(file: UploadFile = File(...)):
    calls.append("upload")
    return {"n": len(file.file.read())}


client = TestClient(app)


def _chunks(total: int, size: int = 100):
    def gen():
        sent = 0
        while sent < total:
            yield b"x" * min(size, total - sent)
            sent += size
    return gen()


def test_small_body_passes():
    r = client.post("/json", json={"data": "a" * 100})
    assert r.status_code == 200 and r.json() == {"n": 100}


def test_content_length_over_limit_rejected_before_endpoint():
    calls.clear()
    r = client.post("/json", json={"data": "a" * (LIMIT * 2)})
    assert r.status_code == 413
    assert "MB" in r.json()["detail"]
    assert calls == []


def test_chunked_body_over_limit_rejected():
    calls.clear()
    # Generator → Content-Length yo'q (Transfer-Encoding: chunked)
    r = client.post(
        "/json", content=_chunks(LIMIT * 3), headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 413
    assert calls == []


def test_chunked_multipart_over_limit_rejected():
    calls.clear()
    boundary = "BOUNDARY"
    head = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.xlsx\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()

    def gen():
        yield head
        yield from _chunks(LIMIT * 3)
        yield f"\r\n--{boundary}--\r\n".encode()

    r = client.post(
        "/upload",
        content=gen(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert r.status_code == 413
    assert calls == []


def test_path_specific_limit():
    payload = {"data": "a" * (LIMIT * 2)}
    assert client.post("/json", json=payload).status_code == 413
    assert client.post("/big/json", json=payload).status_code == 200


def test_main_app_has_body_limit():
    from app.main import app as main_app

    assert any(m.cls is BodySizeLimitMiddleware for m in main_app.user_middleware)

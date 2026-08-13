import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

Base.metadata.create_all(bind=engine)
client=TestClient(app)

def test_root():
    r=client.get("/")
    assert r.status_code == 200

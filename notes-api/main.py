import json
import os
from pathlib import Path

from fastapi import FastAPI

API_TITLE = os.getenv("API_TITLE", "notes-api")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "API activa")
HEALTH_STATUS = os.getenv("HEALTH_STATUS", "ok")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "default")

app = FastAPI(title=API_TITLE)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "notes.json"


def load_notes() -> list[str]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_notes(notes: list[str]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


notes: list[str] = load_notes()


@app.get("/")
def root():
    return {"message": WELCOME_MESSAGE, "title": API_TITLE, "instance": INSTANCE_NAME}


@app.post("/add/{note}")
def add_note(note: str):
    notes.append(note)
    save_notes(notes)
    return {"message": "Nota agregada", "note": note}


@app.get("/list")
def list_notes():
    return {"notes": notes}


@app.get("/health")
def health():
    return {"status": HEALTH_STATUS, "instance": INSTANCE_NAME}

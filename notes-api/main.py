import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()

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
    return {"message": "API activa"}


@app.post("/add/{note}")
def add_note(note: str):
    notes.append(note)
    save_notes(notes)
    return {"message": "Nota agregada", "note": note}


@app.get("/list")
def list_notes():
    return {"notes": notes}

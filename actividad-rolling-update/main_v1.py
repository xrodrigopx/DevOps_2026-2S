import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="notes-api")

DATA_FILE = Path("data/notes.json")
DATA_FILE.parent.mkdir(exist_ok=True)


def load_notes() -> list[str]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return []


def save_notes(notes: list[str]) -> None:
    DATA_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


notes: list[str] = load_notes()


@app.get("/")
def root():
    return {"message": "API activa"}


@app.post("/add/{note}")
def add_note(note: str):
    notes.append(note)
    save_notes(notes)
    return {"message": "Nota agregada", 
            "note": note}


@app.get("/list")
def list_notes():
    return {"notes": notes}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": "v1"}

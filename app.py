"""Web interface: password-protected chat that streams the agent's steps.
Usage: uvicorn app:app --port 8000   then open http://localhost:8000 (password: CHAT_PASSWORD, default "artefact")"""
import json
import os
import secrets
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from emporio.agent import Agent

PASSWORD = os.getenv("CHAT_PASSWORD", "artefact")
MAX_SESSIONS, MAX_TURNS, MAX_CHARS = 500, 40, 1000  # cost guard for a public demo

app = FastAPI()
# ponytail: in-memory sessions, lost on restart; Redis if this ever runs on more than one process
sessions: OrderedDict[str, dict] = OrderedDict()


class ChatIn(BaseModel):
    session_id: str
    message: str
    lang: str = "en"  # "en" or "pt": reply language and language of the step explanations


def check(password):
    if not secrets.compare_digest(password or "", PASSWORD):
        raise HTTPException(401, "Wrong password")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/api/login")
def login(x_password: str = Header(None)):
    check(x_password)
    return {"ok": True}


@app.post("/api/reset")
def reset(body: ChatIn, x_password: str = Header(None)):
    check(x_password)
    sessions.pop(body.session_id, None)
    return {"ok": True}


@app.post("/api/chat")
def chat(body: ChatIn, x_password: str = Header(None)):
    check(x_password)
    if body.session_id not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            sessions.popitem(last=False)  # drop the oldest conversation
        sessions[body.session_id] = {"agent": Agent(), "turns": 0}
    session = sessions[body.session_id]

    def events():
        en = body.lang == "en"
        if session["turns"] >= MAX_TURNS or len(body.message) > MAX_CHARS:
            yield {"type": "answer", "text": "This conversation reached the demo limit. Click Reset to start over." if en else
                                             "Esta conversa atingiu o limite da demonstração. Clique em Reset para recomeçar."}
            return
        session["turns"] += 1
        try:
            yield from session["agent"].stream(body.message.strip(), "en" if en else "pt")
        except Exception as e:  # e.g. OpenAI unavailable: tell the user instead of breaking the stream
            yield {"type": "error", "explain": f"Error calling the model: {e}"}
            yield {"type": "answer", "text": "I had a technical problem. Please try again in a moment." if en else
                                             "Tive um problema técnico agora. Pode tentar de novo em instantes?"}

    return StreamingResponse((json.dumps(e, ensure_ascii=False) + "\n" for e in events()),
                             media_type="application/x-ndjson")

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import requests
import time
import threading
import uvicorn
import uuid
from typing import Optional
import os
import hashlib
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_ipaddr
from slowapi.errors import RateLimitExceeded

endpointurl = "https://dcrelay.liteeagle.me/"

def get_cloudflare_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return get_ipaddr(request)

limiter = Limiter(key_func=get_cloudflare_ip, default_limits=["100/minute"])

app = FastAPI(
    title="Webhook Relayer, By LiteEagle262",
    description="This is a simple FastAPI Powered app that will relay webhook requests, allowing your webhook to be protected from spamming, and deletion.\n\nThe /relay endpoint relays it to your discord webhook, all contents etc remain the same.",
    version="1.0.0"
)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

DATABASE_URL = "sqlite:///./data.sqlite3"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    if not os.path.exists("data.sqlite3"):
        Base.metadata.create_all(bind=engine)
        print("Database initialized and tables created.")
    else:
        print("Database already exists.")

init_db()

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(String(255), primary_key=True, index=True)
    url = Column(String(2048), nullable=False)

Base.metadata.create_all(bind=engine)

class WebhookPayload(BaseModel):
    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    embeds: Optional[list] = None

class CreateWebhook(BaseModel):
    url: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.get("/count_webhooks")
@limiter.limit("100/minute")
def count_webhooks(request: Request, db: Session = Depends(get_db)):
    count = db.query(Webhook).count()
    return {"webhook_count": count}

@app.post("/AddHook")
@limiter.limit("3/minute")
def create_webhook(webhook: CreateWebhook, request: Request, db: Session = Depends(get_db)):
    if not webhook.url.startswith("https://discord.com/api/webhooks/"):
        return {"message": "Invalid Webhook url."}

    id = str(uuid.uuid4())
    new_webhook = Webhook(id=id, url=webhook.url)
    db.add(new_webhook)
    db.commit()
    return {"message": "Webhook created successfully.", "HookURL": f"{endpointurl}relay/{id}"}

async def store_payload_in_state(request: Request, payload: WebhookPayload):
    request.state.json_body = payload.dict(exclude_unset=True)

async def content_hash_key_func(request: Request):
    ip_address = get_cloudflare_ip(request)
    try:
        payload_dict = request.state.json_body
        serialized_payload = str(sorted(payload_dict.items()))
        content_hash = hashlib.md5(serialized_payload.encode('utf-8')).hexdigest()
        return f"{ip_address}:{content_hash}"
    except Exception:
        return ip_address

@app.post("/relay/{webhook_id}")
@limiter.limit("1/15second", key_func=content_hash_key_func, error_message="Duplicate submission detected. Please wait 15 seconds before sending the same content again.")
async def relay_webhook(webhook_id: str, payload: WebhookPayload, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db),
                      _ = Depends(store_payload_in_state)):
    db_webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not db_webhook:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    background_tasks.add_task(sendhook, db_webhook.url, payload.dict(exclude_unset=True))

    return JSONResponse(content={"message": "Webhook relayed successfully."})

def sendhook(webhook_url: str, payload: dict):
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error relaying webhook: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

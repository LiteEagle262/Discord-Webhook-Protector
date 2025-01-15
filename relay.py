from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import requests
import time
import threading
import uvicorn
import uuid
from typing import Optional
import os

endpointurl = "https://dcrelay.liteeagle.me/"

app = FastAPI(
    title="Webhook Relayer, By LiteEagle262",
    description="This is a simple FastAPI Powered app that will relay webhook requests, allowing your webhook to be protected from spamming, and deletion.\n\nThe /relay endpoint relays it to your discord webhook, all contents etc remain the same.",
    version="1.0.0"
)

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

rate_limit_cache = {}
cache_lock = threading.Lock()
webhook_creation_cache = {}
webhook_creation_lock = threading.Lock()

def init_db():
    if not os.path.exists("data.sqlite3"):
        Base.metadata.create_all(bind=engine)
        print("Database initialized and tables created.")
    else:
        print("Database already exists.")

init_db()

# SQLITE Models
class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(String(255), primary_key=True, index=True)
    url = Column(String(2048), nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic Models
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
async def root(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.get("/count_webhooks")
def count_webhooks(db: Session = Depends(get_db)):
    count = db.query(Webhook).count()
    return {"webhook_count": count}

@app.post("/AddHook")
def create_webhook(webhook: CreateWebhook, request: Request, db: Session = Depends(get_db)):
    if not webhook.url.startswith("https://discord.com/api/webhooks/"):
        return {"message": "Invalid Webhook url."}

    current_time = time.time()
    client_ip = request.client.host

    with webhook_creation_lock:
        if client_ip in webhook_creation_cache:
            timestamps = webhook_creation_cache[client_ip]
            timestamps = [ts for ts in timestamps if current_time - ts < 10]
            if len(timestamps) >= 5:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. You can only create 5 webhooks in 10 seconds.")
            timestamps.append(current_time)
            webhook_creation_cache[client_ip] = timestamps
        else:
            webhook_creation_cache[client_ip] = [current_time]

    id = str(uuid.uuid4())
    new_webhook = Webhook(id=id, url=webhook.url)
    db.add(new_webhook)
    db.commit()
    return {"message": "Webhook created successfully.", "HookURL": f"{endpointurl}relay/{id}"}

@app.post("/relay/{webhook_id}")
async def relay_webhook(webhook_id: str, payload: WebhookPayload, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    client_ip = request.client.host

    db_webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not db_webhook:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    cache_key = f"{client_ip}:{webhook_id}:{hash(frozenset(payload.dict().items()))}"
    current_time = time.time()

    with cache_lock:
        if cache_key in rate_limit_cache:
            last_request_time = rate_limit_cache[cache_key]
            if current_time - last_request_time < 30:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait 30 seconds.")

        rate_limit_cache[cache_key] = current_time

    background_tasks.add_task(sendhook, db_webhook.url, payload.dict(exclude_unset=True))

    return JSONResponse(content={"message": "Webhook relayed successfully."})

def sendhook(webhook_url: str, payload: dict):
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error relaying webhook: {e}")

def clean_cache():
    while True:
        with cache_lock:
            current_time = time.time()

            rate_limit_keys_to_remove = [key for key, timestamp in rate_limit_cache.items() if current_time - timestamp > 30]
            for key in rate_limit_keys_to_remove:
                del rate_limit_cache[key]

            with webhook_creation_lock:
                for client_ip, timestamps in list(webhook_creation_cache.items()):
                    webhook_creation_cache[client_ip] = [ts for ts in timestamps if current_time - ts < 10]

                    if not webhook_creation_cache[client_ip]:
                        del webhook_creation_cache[client_ip]

        time.sleep(60)

threading.Thread(target=clean_cache, daemon=True).start()

uvicorn.run(app, host="0.0.0.0", port=8000)
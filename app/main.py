import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.endpoints import residents, rules, shifts, auth, organizations, constraints, google_auth

load_dotenv()

app = FastAPI(title="Call Companion API")

# Configure CORS for frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    for url in frontend_url.split(","):
        url = url.strip()
        if url and url not in origins:
            origins.append(url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Call Companion API"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
app.include_router(constraints.router, prefix="/constraints", tags=["constraints"])
app.include_router(residents.router, prefix="/residents", tags=["residents"])
app.include_router(rules.router, prefix="/rules", tags=["rules"])
app.include_router(shifts.router, prefix="/shifts", tags=["shifts"])
app.include_router(google_auth.router, prefix="/google", tags=["google_auth"])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import residents, rules, shifts, auth, organizations, constraints

app = FastAPI(title="Call Companion API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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

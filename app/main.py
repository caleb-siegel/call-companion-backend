from fastapi import FastAPI
# from backend.app.api.endpoints import residents, shifts # These don't exist yet

app = FastAPI(title="Call Companion API")

@app.get("/")
async def root():
    return {"message": "Welcome to Call Companion API"}

# Include routers here as they are developed
# app.include_router(residents.router, prefix="/residents", tags=["residents"])
# app.include_router(shifts.router, prefix="/shifts", tags=["shifts"])

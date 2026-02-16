from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import engine, Base
from app.config.settings import settings
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.systems.router import router as systems_router
from app.features.access.router import router as access_router
from app.features.audit.router import router as audit_router

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# CORS Configuration
# In a real scenario, you'd fetch allowed origins from the DB or a strict list
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(systems_router)
app.include_router(access_router)
app.include_router(audit_router)

@app.get("/")
def read_root():
    return {"message": "Central Auth Hub is running"}

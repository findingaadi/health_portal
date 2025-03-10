from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine
from app.models import Base
from app.routes import user_routes, record_routes

app = FastAPI()

ALLOWED_ORIGINS = ["http://127.0.0.1:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Allow only the frontend domain
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],  # Only allow required HTTP methods
    allow_headers=["Authorization", "Content-Type"],  # Only allow necessary headers
)

# Create all tables
Base.metadata.create_all(bind=engine)

# Include the routers
app.include_router(user_routes.router)
app.include_router(record_routes.router)

app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

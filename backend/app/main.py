from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routes import user_routes, record_routes

app = FastAPI()

# Create all tables
Base.metadata.create_all(bind=engine)

# Include the routers
app.include_router(user_routes.router)
app.include_router(record_routes.router)
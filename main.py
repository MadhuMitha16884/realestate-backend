from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Real Estate Backend is running!"}
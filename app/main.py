from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.routes import router
from app.models import Rover
from app.seed import seed_initial_data


def init_db():
    """Initialize database with default data if empty."""
    db = SessionLocal()
    try:
        if db.query(Rover).first():
            return
        seed_initial_data(db)
        print("Database initialized with default data")
    except Exception as e:
        print(f"Init error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    init_db()
    yield


app = FastAPI(
    title="Moon Courier Crisis API",
    description="Backend for Moon Courier Crisis game",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Moon Courier Crisis API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}

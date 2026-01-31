from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from config import settings
from database import init_db
from routes import router


# Initialize FastAPI app
app = FastAPI(title="MamaShield AI", version="0.1")

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# SMS disclaimer
DISCLAIMER = settings.SMS_DISCLAIMER


@app.on_event("startup")
async def startup():
    """Initialize database on application startup."""
    await init_db()


@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "MamaShield AI running"}


# Include routers
app.include_router(router)


from fastapi import FastAPI

app = FastAPI(
    title="CloudCapsule API",
    description="Cloud module lifecycle management platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "CloudCapsule",
        "message": "CloudCapsule API is running",
        "mode": "local-development",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "cloudcapsule-api",
        "mode": "local-development",
    }

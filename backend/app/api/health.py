from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-dev-team-backend"
    }


@router.get("/health/ready")
async def readiness_check():
    return {
        "status": "ready",
        "services": {
            "api": "ready",
            "database": "not_configured",
            "qdrant": "not_configured"
        }
    }

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.FastAPI.anomaly_routes import router as anomaly_router, detector
from data_processing.anomaly_repository import ensure_anomaly_tables


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_engine")


def configured_origins() -> list[str]:
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8086")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing analysis engine")
    try:
        ensure_anomaly_tables()
        loaded = detector.model.load()
        if loaded:
            logger.info("Loaded existing Isolation Forest model")
        else:
            logger.info("No saved model found; training from parsed logs if data is available")
            logger.info("Initial training result: %s", detector.train_from_scratch())
    except Exception as error:
        logger.error("Analysis engine startup initialization failed: %s", error)

    yield

    logger.info("Shutting down analysis engine")


app = FastAPI(
    title="Intelligent Log Analysis Platform - Analysis Engine",
    description="FastAPI service for log anomaly detection using Isolation Forest",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anomaly_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": detector.model.is_trained,
        "encoders_loaded": bool(detector.engineer.encoders),
    }

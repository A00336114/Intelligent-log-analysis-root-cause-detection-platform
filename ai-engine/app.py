import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.FastAPI.anomaly_routes import router as anomaly_router, detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_engine")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Try to load existing model/encoders or train on startup if data is available
    logger.info("Initializing AI Engine lifespan...")
    try:
        loaded = detector.model.load()
        if loaded:
            logger.info("Successfully loaded existing Isolation Forest model from disk.")
        else:
            logger.info("No pre-existing Isolation Forest model found. Attempting initial training...")
            train_res = detector.train_from_scratch()
            logger.info(f"Initial training status: {train_res}")
    except Exception as e:
        logger.error(f"Error during AI Engine startup training initialization: {e}")
    
    yield
    
    logger.info("Shutting down AI Engine lifespan...")

app = FastAPI(
    title="Intelligent Log Analysis Platform — AI Engine",
    description="FastAPI service for Anomaly Detection using Isolation Forest",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(anomaly_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": detector.model.is_trained,
        "encoders_loaded": bool(detector.engineer.encoders)
    }
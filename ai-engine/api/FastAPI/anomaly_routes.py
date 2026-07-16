import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from api.FastAPI.schemas import (
    AnomalyDetectRequest, 
    AnomalyDetectBatchRequest, 
    AnomalyResultResponse, 
    AnomalyStatusResponse
)
from anomaly_detection.inference.anomaly_detector import AnomalyDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anomaly", tags=["anomaly"])
detector = AnomalyDetector()

@router.post("/detect", response_model=AnomalyResultResponse)
def detect_anomaly(payload: AnomalyDetectRequest):
    try:
        res = detector.detect_anomaly(payload.incident_id)
        return res
    except Exception as e:
        logger.error(f"Error in anomaly detection route for incident {payload.incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-batch", response_model=List[AnomalyResultResponse])
def detect_anomalies_batch(payload: AnomalyDetectBatchRequest):
    try:
        res = detector.detect_anomalies_batch(payload.incident_ids)
        return res
    except Exception as e:
        logger.error(f"Error in anomaly batch detection route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def background_train():
    try:
        logger.info("Starting background training...")
        res = detector.train_from_scratch()
        logger.info(f"Background training finished: {res}")
    except Exception as e:
        logger.error(f"Background training failed: {e}")

@router.post("/train")
def train_model(background_tasks: BackgroundTasks):
    background_tasks.add_task(background_train)
    return {"status": "training_started", "message": "Model training has been scheduled in the background."}

@router.get("/status", response_model=AnomalyStatusResponse)
def get_model_status():
    return detector.get_status()

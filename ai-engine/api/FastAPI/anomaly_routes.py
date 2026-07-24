import logging
from fastapi import APIRouter, HTTPException
from typing import List
from api.FastAPI.schemas import (
    AnomalyDetectRequest, 
    AnomalyDetectBatchRequest, 
    AnomalyResultResponse, 
    AnomalyStatusResponse,
    RecommendationResponse,
    SimilarIncidentResponse,
)
from anomaly_detection.inference.anomaly_detector import AnomalyDetector
from root_cause_recommendation.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["anomaly"])
detector = AnomalyDetector()
recommendation_service = RecommendationService()

@router.post("/detect-anomaly", response_model=AnomalyResultResponse)
@router.post("/api/anomaly/detect", response_model=AnomalyResultResponse)
def detect_anomaly(payload: AnomalyDetectRequest):
    try:
        res = detector.detect_anomaly(payload.incident_id)
        return res
    except Exception as e:
        logger.error(f"Error in anomaly detection route for incident {payload.incident_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-anomalies", response_model=List[AnomalyResultResponse])
@router.post("/api/anomaly/detect-batch", response_model=List[AnomalyResultResponse])
def detect_anomalies_batch(payload: AnomalyDetectBatchRequest):
    try:
        res = detector.detect_anomalies_batch(payload.incident_ids)
        return res
    except Exception as e:
        logger.error(f"Error in anomaly batch detection route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train")
@router.post("/api/anomaly/train")
def train_model():
    try:
        logger.info("Starting model training...")
        res = detector.train_from_scratch()
        logger.info(f"Model training finished: {res}")
        return res
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies", response_model=List[AnomalyResultResponse])
@router.get("/api/anomaly/results", response_model=List[AnomalyResultResponse])
def get_anomaly_results():
    try:
        return detector.get_results()
    except Exception as e:
        logger.error(f"Error fetching anomaly results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies/{incident_id}", response_model=AnomalyResultResponse)
@router.get("/api/anomaly/results/{incident_id}", response_model=AnomalyResultResponse)
def get_anomaly_result(incident_id: int):
    result = detector.get_result_by_incident_id(incident_id)
    if not result:
        raise HTTPException(status_code=404, detail="Anomaly result not found")
    return result

@router.get("/status", response_model=AnomalyStatusResponse)
@router.get("/api/anomaly/status", response_model=AnomalyStatusResponse)
def get_model_status():
    return detector.get_status()


@router.get("/similar-incidents/{incident_id}", response_model=List[SimilarIncidentResponse], tags=["recommendations"])
@router.get("/api/recommendations/similar/{incident_id}", response_model=List[SimilarIncidentResponse], tags=["recommendations"])
def find_similar_incidents(incident_id: int):
    return recommendation_service.find_similar_incidents(incident_id)


@router.post("/recommendations/{incident_id}", response_model=RecommendationResponse, tags=["recommendations"])
@router.post("/api/recommendations/generate/{incident_id}", response_model=RecommendationResponse, tags=["recommendations"])
def generate_recommendation(incident_id: int):
    try:
        return recommendation_service.generate_recommendation(incident_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        logger.error("Recommendation generation failed for incident %s: %s", incident_id, error)
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/recommendations", response_model=List[RecommendationResponse], tags=["recommendations"])
@router.get("/api/recommendations", response_model=List[RecommendationResponse], tags=["recommendations"])
def get_recommendations():
    return recommendation_service.get_recommendations()


@router.get("/recommendations/{incident_id}", response_model=RecommendationResponse, tags=["recommendations"])
@router.get("/api/recommendations/{incident_id}", response_model=RecommendationResponse, tags=["recommendations"])
def get_recommendation(incident_id: int):
    recommendation = recommendation_service.get_recommendation(incident_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation

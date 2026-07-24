from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class AnomalyDetectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    incident_id: int = Field(..., serialization_alias="incidentId", validation_alias="incidentId")

class AnomalyDetectBatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    incident_ids: List[int] = Field(..., serialization_alias="incidentIds", validation_alias="incidentIds")

class AnomalyResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())
    id: Optional[int] = None
    incident_id: int = Field(..., serialization_alias="incidentId")
    is_anomaly: bool = Field(..., serialization_alias="isAnomaly")
    anomaly_score: float = Field(..., serialization_alias="anomalyScore")
    reason: str
    model_version: Optional[str] = Field(None, serialization_alias="modelVersion")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt")

class AnomalyStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())
    model_trained: bool = Field(..., serialization_alias="modelTrained")
    encoders_loaded: bool = Field(..., serialization_alias="encodersLoaded")
    contamination: float
    results_saved: int = Field(0, serialization_alias="resultsSaved")


class SimilarIncidentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    incident_id: int = Field(..., serialization_alias="incidentId")
    incident_number: Optional[str] = Field(None, serialization_alias="incidentNumber")
    alert_name: Optional[str] = Field(None, serialization_alias="alertName")
    service_name: Optional[str] = Field(None, serialization_alias="serviceName")
    status: Optional[str] = None
    severity: Optional[str] = None
    similarity_score: float = Field(..., serialization_alias="similarityScore")
    notes: Optional[str] = None
    raw_log: Optional[str] = Field(None, serialization_alias="rawLog")
    parsed_log: Optional[dict] = Field(None, serialization_alias="parsedLog")


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())
    id: int
    incident_id: int = Field(..., serialization_alias="incidentId")
    similar_incident_id: Optional[int] = Field(None, serialization_alias="similarIncidentId")
    similarity_score: float = Field(..., serialization_alias="similarityScore")
    recommended_root_cause: str = Field(..., serialization_alias="recommendedRootCause")
    recommended_fix: str = Field(..., serialization_alias="recommendedFix")
    evidence: Optional[str] = None
    model_used: str = Field(..., serialization_alias="modelUsed")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt")
    similar_incidents: List[SimilarIncidentResponse] = Field(default_factory=list, serialization_alias="similarIncidents")

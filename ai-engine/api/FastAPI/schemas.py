from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

# Week 8 — Anomaly Detection schemas
class AnomalyDetectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    incident_id: int = Field(..., serialization_alias="incidentId", validation_alias="incidentId")

class AnomalyDetectBatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    incident_ids: List[int] = Field(..., serialization_alias="incidentIds", validation_alias="incidentIds")

class AnomalyResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: Optional[int] = None
    incident_id: int = Field(..., serialization_alias="incidentId")
    is_anomaly: bool = Field(..., serialization_alias="isAnomaly")
    anomaly_score: float = Field(..., serialization_alias="anomalyScore")
    reason: str
    model_version: Optional[str] = Field(None, serialization_alias="modelVersion")
    created_at: Optional[str] = Field(None, serialization_alias="createdAt")
    updated_at: Optional[str] = Field(None, serialization_alias="updatedAt")

class AnomalyStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    model_trained: bool = Field(..., serialization_alias="modelTrained")
    encoders_loaded: bool = Field(..., serialization_alias="encodersLoaded")
    contamination: float
    results_saved: int = Field(0, serialization_alias="resultsSaved")

# Week 9 — Similarity Search & RCA schemas
class SimilarIncidentResponse(BaseModel):
    id: int
    score: float
    service_name: Optional[str] = Field(None, serialization_alias="serviceName")
    failure_type: Optional[str] = Field(None, serialization_alias="failureType")
    notes: Optional[str] = None
    raw_log: Optional[str] = Field(None, serialization_alias="rawLog")

class SimilarSearchRequest(BaseModel):
    incident_id: Optional[int] = Field(None, serialization_alias="incidentId", validation_alias="incidentId")
    text: Optional[str] = None

class RebuildIndexResponse(BaseModel):
    status: str
    n_incidents_indexed: int = Field(..., serialization_alias="nIncidentsIndexed")

class IndexStatusResponse(BaseModel):
    n_incidents_indexed: int = Field(..., serialization_alias="nIncidentsIndexed")
    last_built_at: Optional[str] = Field(None, serialization_alias="lastBuiltAt")

class RecoveryActionResponse(BaseModel):
    id: int
    incident_id: int = Field(..., serialization_alias="incidentId")
    action_name: str = Field(..., serialization_alias="actionName")
    action_args: dict = Field(..., serialization_alias="actionArgs")
    action_result: Optional[str] = Field(None, serialization_alias="actionResult")
    llm_reason: Optional[str] = Field(None, serialization_alias="llmReason")
    executed_at: str = Field(..., serialization_alias="executedAt")
    success: bool

class RecoveryReportResponse(BaseModel):
    incident_id: int = Field(..., serialization_alias="incidentId")
    root_cause: str = Field(..., serialization_alias="rootCause")
    action_taken: str = Field(..., serialization_alias="actionTaken")
    action_result: str = Field(..., serialization_alias="actionResult")
    llm_summary: str = Field(..., serialization_alias="llmSummary")
    similar_incident_ids: List[int] = Field(..., serialization_alias="similarIncidentIds")
    model_used: str = Field(..., serialization_alias="modelUsed")
    analyzed_at: str = Field(..., serialization_alias="analyzedAt")

import os
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
    desc,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def build_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    database = os.getenv("POSTGRES_DB", "platform_db")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class ParsedLogRecord(Base):
    __tablename__ = "parsed_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    service_name: Mapped[str | None] = mapped_column(String(120))
    log_level: Mapped[str | None] = mapped_column(String(16))
    error_message: Mapped[str | None] = mapped_column(Text)
    exception_type: Mapped[str | None] = mapped_column(String(255))
    status_code: Mapped[int | None] = mapped_column(Integer)
    trace_id: Mapped[str | None] = mapped_column(String(255))
    failure_type: Mapped[str | None] = mapped_column(String(120))
    log_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    raw_log: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AnomalyResultRecord(Base):
    __tablename__ = "anomaly_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="isolation-forest-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_name: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    incident_number: Mapped[str | None] = mapped_column(String(255))
    service_name: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(255))
    raw_payload: Mapped[str | None] = mapped_column(Text)
    raw_log: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(String(255))
    parser_status: Mapped[str | None] = mapped_column(String(255))
    parser_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)


class RootCauseRecommendationRecord(Base):
    __tablename__ = "root_cause_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    similar_incident_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommended_root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_fix: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(80), nullable=False, default="rules-and-similarity")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def ensure_anomaly_tables() -> None:
    Base.metadata.create_all(
        bind=engine,
        tables=[
            AnomalyResultRecord.__table__,
            RootCauseRecommendationRecord.__table__,
        ],
    )


def parsed_log_to_dict(record: ParsedLogRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "incidentId": record.incident_id,
        "timestamp": record.log_timestamp.isoformat() if record.log_timestamp else None,
        "serviceName": record.service_name,
        "logLevel": record.log_level,
        "errorMessage": record.error_message,
        "exceptionType": record.exception_type,
        "statusCode": record.status_code,
        "traceId": record.trace_id,
        "failureType": record.failure_type,
        "rawLog": record.raw_log,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


def anomaly_to_dict(record: AnomalyResultRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "incident_id": record.incident_id,
        "is_anomaly": record.is_anomaly,
        "anomaly_score": record.anomaly_score,
        "reason": record.reason,
        "model_version": record.model_version,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def incident_to_dict(record: IncidentRecord, parsed_log: ParsedLogRecord | None = None) -> dict[str, Any]:
    parsed = parsed_log_to_dict(parsed_log) if parsed_log else None
    return {
        "id": record.id,
        "incidentNumber": record.incident_number,
        "alertName": record.alert_name,
        "title": record.title,
        "description": record.description,
        "serviceName": record.service_name,
        "severity": record.severity,
        "status": record.status,
        "source": record.source,
        "rawLog": record.raw_log,
        "traceId": record.trace_id,
        "parserStatus": record.parser_status,
        "parserMessage": record.parser_message,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
        "parsedAt": record.parsed_at.isoformat() if record.parsed_at else None,
        "updatedAt": record.updated_at.isoformat() if record.updated_at else None,
        "resolvedAt": record.resolved_at.isoformat() if record.resolved_at else None,
        "notes": record.notes,
        "parsedLog": parsed,
    }


def recommendation_to_dict(record: RootCauseRecommendationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "incident_id": record.incident_id,
        "similar_incident_id": record.similar_incident_id,
        "similarity_score": record.similarity_score,
        "recommended_root_cause": record.recommended_root_cause,
        "recommended_fix": record.recommended_fix,
        "evidence": record.evidence,
        "model_used": record.model_used,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


class AnomalyRepository:
    def fetch_all_parsed_logs(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = session.execute(
                select(ParsedLogRecord).order_by(ParsedLogRecord.created_at.desc(), ParsedLogRecord.id.desc())
            ).scalars().all()
            return [parsed_log_to_dict(record) for record in records]

    def fetch_parsed_log_by_incident_id(self, incident_id: int) -> dict[str, Any] | None:
        with SessionLocal() as session:
            record = session.execute(
                select(ParsedLogRecord).where(ParsedLogRecord.incident_id == incident_id)
            ).scalar_one_or_none()
            return parsed_log_to_dict(record) if record else None

    def save_result(
        self,
        incident_id: int,
        is_anomaly: bool,
        anomaly_score: float,
        reason: str,
        model_version: str = "isolation-forest-v1",
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            record = session.execute(
                select(AnomalyResultRecord).where(AnomalyResultRecord.incident_id == incident_id)
            ).scalar_one_or_none()

            if record is None:
                record = AnomalyResultRecord(incident_id=incident_id)
                session.add(record)

            record.is_anomaly = is_anomaly
            record.anomaly_score = anomaly_score
            record.reason = reason
            record.model_version = model_version
            record.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(record)
            return anomaly_to_dict(record)

    def fetch_results(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = session.execute(
                select(AnomalyResultRecord).order_by(
                    AnomalyResultRecord.updated_at.desc(),
                    AnomalyResultRecord.id.desc(),
                )
            ).scalars().all()
            return [anomaly_to_dict(record) for record in records]

    def fetch_result_by_incident_id(self, incident_id: int) -> dict[str, Any] | None:
        with SessionLocal() as session:
            record = session.execute(
                select(AnomalyResultRecord).where(AnomalyResultRecord.incident_id == incident_id)
            ).scalar_one_or_none()
            return anomaly_to_dict(record) if record else None

    def fetch_incident_with_parsed_log(self, incident_id: int) -> dict[str, Any] | None:
        with SessionLocal() as session:
            incident = session.execute(
                select(IncidentRecord).where(IncidentRecord.id == incident_id)
            ).scalar_one_or_none()
            if incident is None:
                return None

            parsed_log = session.execute(
                select(ParsedLogRecord).where(ParsedLogRecord.incident_id == incident_id)
            ).scalar_one_or_none()
            return incident_to_dict(incident, parsed_log)

    def fetch_incidents_for_similarity(self, exclude_incident_id: int | None = None) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            query = (
                select(IncidentRecord, ParsedLogRecord)
                .outerjoin(ParsedLogRecord, ParsedLogRecord.incident_id == IncidentRecord.id)
                .order_by(desc(IncidentRecord.resolved_at), desc(IncidentRecord.updated_at), desc(IncidentRecord.id))
            )
            if exclude_incident_id is not None:
                query = query.where(IncidentRecord.id != exclude_incident_id)

            rows = session.execute(query).all()
            return [incident_to_dict(incident, parsed_log) for incident, parsed_log in rows]

    def save_recommendation(
        self,
        incident_id: int,
        similar_incident_id: int | None,
        similarity_score: float,
        recommended_root_cause: str,
        recommended_fix: str,
        evidence: str,
        model_used: str,
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            record = session.execute(
                select(RootCauseRecommendationRecord).where(
                    RootCauseRecommendationRecord.incident_id == incident_id
                )
            ).scalar_one_or_none()

            if record is None:
                record = RootCauseRecommendationRecord(incident_id=incident_id)
                session.add(record)

            record.similar_incident_id = similar_incident_id
            record.similarity_score = similarity_score
            record.recommended_root_cause = recommended_root_cause
            record.recommended_fix = recommended_fix
            record.evidence = evidence
            record.model_used = model_used
            record.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(record)
            return recommendation_to_dict(record)

    def fetch_recommendation_by_incident_id(self, incident_id: int) -> dict[str, Any] | None:
        with SessionLocal() as session:
            record = session.execute(
                select(RootCauseRecommendationRecord).where(
                    RootCauseRecommendationRecord.incident_id == incident_id
                )
            ).scalar_one_or_none()
            return recommendation_to_dict(record) if record else None

    def fetch_recommendations(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            records = session.execute(
                select(RootCauseRecommendationRecord).order_by(
                    RootCauseRecommendationRecord.updated_at.desc(),
                    RootCauseRecommendationRecord.id.desc(),
                )
            ).scalars().all()
            return [recommendation_to_dict(record) for record in records]

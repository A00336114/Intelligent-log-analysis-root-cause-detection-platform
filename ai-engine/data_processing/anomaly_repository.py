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
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://admin:password@postgres:5432/platform_db",
)

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


def ensure_anomaly_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[AnomalyResultRecord.__table__])


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

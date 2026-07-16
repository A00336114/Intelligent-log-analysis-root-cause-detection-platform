import os
import time
from datetime import datetime
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, DateTime, Integer, String, Text, create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from parser_core import extract_fields

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://admin:password@postgres:5432/platform_db",
)

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class ParsedLog(Base):
    __tablename__ = "parsed_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    service_name: Mapped[str | None] = mapped_column(String(120))
    log_level: Mapped[str | None] = mapped_column(String(16))
    error_message: Mapped[str | None] = mapped_column(Text)
    exception_type: Mapped[str | None] = mapped_column(String(255))
    status_code: Mapped[int | None] = mapped_column(Integer)
    trace_id: Mapped[str | None] = mapped_column(String(255))
    failure_type: Mapped[str | None] = mapped_column(String(120))
    log_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    raw_log: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class ParseLogRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    incident_id: int = Field(alias="incidentId")
    raw_log: str = Field(alias="rawLog")
    service_name: str | None = Field(default=None, alias="serviceName")
    timestamp: datetime | None = None
    trace_id: str | None = Field(default=None, alias="traceId")
    status_code: int | None = Field(default=None, alias="statusCode")
    failure_type: str | None = Field(default=None, alias="failureType")
    error_message: str | None = Field(default=None, alias="errorMessage")


class ParseLogResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    incident_id: int = Field(alias="incidentId")
    timestamp: str | None
    service_name: str | None = Field(alias="serviceName")
    log_level: str | None = Field(alias="logLevel")
    error_message: str | None = Field(alias="errorMessage")
    exception_type: str | None = Field(alias="exceptionType")
    status_code: int | None = Field(alias="statusCode")
    trace_id: str | None = Field(alias="traceId")
    failure_type: str | None = Field(alias="failureType")
    created_at: str = Field(alias="createdAt")


app = FastAPI(title="log-parser-service")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    ensure_database_ready()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/parse-log", response_model=ParseLogResponse)
def parse_log(payload: ParseLogRequest, db: Session = Depends(get_db)) -> ParseLogResponse:
    parsed = extract_fields(payload)

    record = db.execute(
        select(ParsedLog).where(ParsedLog.incident_id == payload.incident_id)
    ).scalar_one_or_none()

    if record is None:
        record = ParsedLog(incident_id=payload.incident_id, raw_log=payload.raw_log)
        db.add(record)

    record.service_name = parsed["service_name"]
    record.log_level = parsed["log_level"]
    record.error_message = parsed["error_message"]
    record.exception_type = parsed["exception_type"]
    record.status_code = parsed["status_code"]
    record.trace_id = parsed["trace_id"]
    record.failure_type = parsed["failure_type"]
    record.log_timestamp = parsed["timestamp"]
    record.raw_log = payload.raw_log

    db.commit()
    db.refresh(record)

    return to_response(record)


@app.get("/parsed-logs", response_model=list[ParseLogResponse])
def get_parsed_logs(db: Session = Depends(get_db)) -> list[ParseLogResponse]:
    records = db.execute(
        select(ParsedLog).order_by(ParsedLog.created_at.desc(), ParsedLog.id.desc())
    ).scalars().all()
    return [to_response(record) for record in records]


@app.get("/parsed-logs/{incident_id}", response_model=ParseLogResponse)
def get_parsed_log(incident_id: int, db: Session = Depends(get_db)) -> ParseLogResponse:
    record = db.execute(
        select(ParsedLog).where(ParsedLog.incident_id == incident_id)
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Parsed log not found")

    return to_response(record)


def ensure_database_ready() -> None:
    last_error: Exception | None = None
    for _ in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError as error:
            last_error = error
            time.sleep(3)

    raise RuntimeError("Unable to initialize parsed_logs table") from last_error


def to_response(record: ParsedLog) -> ParseLogResponse:
    return ParseLogResponse(
        id=record.id,
        incidentId=record.incident_id,
        timestamp=record.log_timestamp.isoformat() if record.log_timestamp else None,
        serviceName=record.service_name,
        logLevel=record.log_level,
        errorMessage=record.error_message,
        exceptionType=record.exception_type,
        statusCode=record.status_code,
        traceId=record.trace_id,
        failureType=record.failure_type,
        createdAt=record.created_at.isoformat(),
    )

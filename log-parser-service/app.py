import os
import re
import time
from datetime import datetime
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, DateTime, Integer, String, Text, create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://admin:password@postgres:5432/platform_db",
)

TIMESTAMP_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?)"
)
LOG_LEVEL_PATTERN = re.compile(r"\b(INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\b")
SERVICE_PATTERN = re.compile(r"\bservice(?:_name)?[=:]\s*(?P<service>[A-Za-z0-9._-]+)")
STATUS_CODE_PATTERN = re.compile(r"\bstatus(?:Code)?[=:]\s*(?P<status>\d{3})\b", re.IGNORECASE)
TRACE_ID_PATTERN = re.compile(r"\btrace(?:Id|_id)?[=:]\s*(?P<trace>[A-Za-z0-9-]+)\b")
FAILURE_TYPE_PATTERN = re.compile(r"\bfailure(?:Type)?[=:]\s*(?P<failure>[A-Za-z0-9_-]+)\b", re.IGNORECASE)
MESSAGE_PATTERN = re.compile(r"\bmessage[=:]\s*(?P<message>.+)", re.IGNORECASE)
EXCEPTION_PATTERN = re.compile(r"\b(?P<exception>[A-Za-z0-9_.]+(?:Exception|Error))\b")

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


def extract_fields(payload: ParseLogRequest) -> dict[str, object | None]:
    raw_log = payload.raw_log
    exception_type = extract_exception_type(raw_log)
    error_message = extract_error_message(raw_log, exception_type, payload.error_message)
    status_code = extract_status_code(raw_log, payload.status_code)

    return {
        "timestamp": extract_timestamp(raw_log, payload.timestamp),
        "service_name": extract_service_name(raw_log, payload.service_name),
        "log_level": extract_log_level(raw_log),
        "error_message": error_message,
        "exception_type": exception_type,
        "status_code": status_code,
        "trace_id": extract_trace_id(raw_log, payload.trace_id),
        "failure_type": extract_failure_type(
            raw_log,
            payload.failure_type,
            exception_type,
            error_message,
            status_code,
        ),
    }


def extract_timestamp(raw_log: str, fallback: datetime | None) -> datetime | None:
    match = TIMESTAMP_PATTERN.search(raw_log)
    if match:
        parsed = parse_datetime(match.group("timestamp"))
        if parsed is not None:
            return parsed
    return fallback


def extract_service_name(raw_log: str, fallback: str | None) -> str | None:
    match = SERVICE_PATTERN.search(raw_log)
    if match:
        return match.group("service")
    return fallback


def extract_log_level(raw_log: str) -> str | None:
    match = LOG_LEVEL_PATTERN.search(raw_log)
    return match.group(1) if match else None


def extract_status_code(raw_log: str, fallback: int | None) -> int | None:
    match = STATUS_CODE_PATTERN.search(raw_log)
    if match:
        return int(match.group("status"))
    return fallback


def extract_trace_id(raw_log: str, fallback: str | None) -> str | None:
    match = TRACE_ID_PATTERN.search(raw_log)
    if match:
        return match.group("trace")
    return fallback


def extract_failure_type(
    raw_log: str,
    fallback: str | None,
    exception_type: str | None,
    error_message: str | None,
    status_code: int | None,
) -> str:
    match = FAILURE_TYPE_PATTERN.search(raw_log)
    if match:
        return normalize_failure_type(match.group("failure"))

    if fallback:
        return normalize_failure_type(fallback)

    combined = f"{exception_type or ''} {error_message or ''} {raw_log}".lower()

    if "timeout" in combined:
        return "TIMEOUT"
    if "invalid login" in combined or "authentication" in combined or status_code == 401:
        return "AUTHENTICATION_FAILURE"
    if "blocked" in combined and "payment" in combined:
        return "PAYMENT_BLOCKED"
    if status_code is not None and status_code >= 500:
        return "SERVER_ERROR"
    if status_code is not None and status_code >= 400:
        return "CLIENT_ERROR"
    return "APPLICATION_FAILURE"


def extract_exception_type(raw_log: str) -> str | None:
    match = EXCEPTION_PATTERN.search(raw_log)
    return match.group("exception") if match else None


def extract_error_message(
    raw_log: str,
    exception_type: str | None,
    fallback: str | None,
) -> str | None:
    if exception_type:
        marker = f"{exception_type}:"
        position = raw_log.find(marker)
        if position >= 0:
            return raw_log[position + len(marker):].strip()

    message_match = MESSAGE_PATTERN.search(raw_log)
    if message_match:
        return message_match.group("message").strip()

    if " - " in raw_log:
        return raw_log.split(" - ", 1)[1].strip()

    return fallback or raw_log.strip()


def parse_datetime(value: str) -> datetime | None:
    candidates = (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )

    normalized = value.replace("Z", "+00:00")
    for pattern in candidates:
        try:
            parsed = datetime.strptime(normalized, pattern)
            if parsed.tzinfo is not None:
                return parsed.astimezone().replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    return None


def normalize_failure_type(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper())
    return cleaned.strip("_") or "APPLICATION_FAILURE"


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

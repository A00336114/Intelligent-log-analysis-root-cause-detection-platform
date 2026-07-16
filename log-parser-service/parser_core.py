import re
from datetime import datetime
from typing import Protocol


class LogPayload(Protocol):
    raw_log: str
    service_name: str | None
    timestamp: datetime | None
    trace_id: str | None
    status_code: int | None
    failure_type: str | None
    error_message: str | None


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


def extract_fields(payload: LogPayload) -> dict[str, object | None]:
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

import unittest
from datetime import datetime
from types import SimpleNamespace

from parser_core import extract_fields


class LogParserExtractionTest(unittest.TestCase):
    def test_extracts_fields_from_raw_error_log(self):
        payload = SimpleNamespace(
            incident_id=42,
            raw_log=(
                "2026-07-12 10:15:00 ERROR service=user-service "
                "traceId=trace-parser-test status=500 failure=server_error "
                "java.lang.IllegalStateException: User service is down"
            ),
            service_name=None,
            timestamp=None,
            trace_id=None,
            status_code=None,
            failure_type=None,
            error_message=None,
        )

        parsed = extract_fields(payload)

        self.assertEqual(datetime(2026, 7, 12, 10, 15), parsed["timestamp"])
        self.assertEqual("user-service", parsed["service_name"])
        self.assertEqual("ERROR", parsed["log_level"])
        self.assertEqual("User service is down", parsed["error_message"])
        self.assertEqual("java.lang.IllegalStateException", parsed["exception_type"])
        self.assertEqual(500, parsed["status_code"])
        self.assertEqual("trace-parser-test", parsed["trace_id"])
        self.assertEqual("SERVER_ERROR", parsed["failure_type"])

    def test_uses_payload_fallbacks_when_raw_log_is_missing_optional_fields(self):
        payload = SimpleNamespace(
            incident_id=43,
            raw_log="payment validation failed",
            service_name="payment-service",
            timestamp=None,
            trace_id="fallback-trace",
            status_code=402,
            failure_type="payment blocked",
            error_message="Card was blocked",
        )

        parsed = extract_fields(payload)

        self.assertEqual("payment-service", parsed["service_name"])
        self.assertEqual("fallback-trace", parsed["trace_id"])
        self.assertEqual(402, parsed["status_code"])
        self.assertEqual("PAYMENT_BLOCKED", parsed["failure_type"])
        self.assertEqual("Card was blocked", parsed["error_message"])


if __name__ == "__main__":
    unittest.main()

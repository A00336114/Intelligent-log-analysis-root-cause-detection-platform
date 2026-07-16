import logging
import os
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LogFetcher:
    def __init__(self, parser_base_url: Optional[str] = None):
        self.parser_base_url = parser_base_url or os.getenv(
            "LOG_PARSER_BASE_URL", "http://log-parser-service:5000"
        )

    def fetch_all_parsed_logs(self) -> List[Dict[str, Any]]:
        """Fetches all parsed logs from the log-parser-service."""
        url = f"{self.parser_base_url}/parsed-logs"
        try:
            logger.info(f"Fetching parsed logs from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching parsed logs: {e}")
            return []

    def fetch_parsed_log_by_incident_id(self, incident_id: int) -> Optional[Dict[str, Any]]:
        """Fetches a specific parsed log by its incident ID."""
        url = f"{self.parser_base_url}/parsed-logs/{incident_id}"
        try:
            logger.info(f"Fetching parsed log for incident {incident_id} from {url}")
            response = requests.get(url, timeout=5)
            if response.status_code == 404:
                logger.warning(f"Parsed log not found for incident {incident_id}")
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching parsed log for incident {incident_id}: {e}")
            return None

    def fetch_as_dataframe(self) -> pd.DataFrame:
        """Fetches all parsed logs and returns them as a pandas DataFrame."""
        logs = self.fetch_all_parsed_logs()
        if not logs:
            return pd.DataFrame()
        return pd.DataFrame(logs)

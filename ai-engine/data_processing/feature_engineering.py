import logging
import pickle
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

DEFAULT_SERVICES = ["user-service", "transaction-service", "payment-service", 
                    "incident-service", "log-parser-service", "log-generator-service"]
DEFAULT_FAILURE_TYPES = ["TIMEOUT", "AUTHENTICATION_FAILURE", "PAYMENT_BLOCKED", 
                         "SERVER_ERROR", "CLIENT_ERROR", "APPLICATION_FAILURE"]

class FeatureEngineer:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.encoders: Dict[str, LabelEncoder] = {}
        self.encoders_path = os.path.join(models_dir, "encoders.pkl")

    def load_encoders(self) -> bool:
        """Loads fit encoders from disk if they exist."""
        if os.path.exists(self.encoders_path):
            try:
                with open(self.encoders_path, 'rb') as f:
                    self.encoders = pickle.load(f)
                logger.info(f"Loaded encoders from {self.encoders_path}")
                return True
            except Exception as e:
                logger.error(f"Error loading encoders: {e}")
        return False

    def save_encoders(self) -> None:
        """Saves fit encoders to disk."""
        os.makedirs(self.models_dir, exist_ok=True)
        try:
            with open(self.encoders_path, 'wb') as f:
                pickle.dump(self.encoders, f)
            logger.info(f"Saved encoders to {self.encoders_path}")
        except Exception as e:
            logger.error(f"Error saving encoders: {e}")

    def fit_encoders(self, df: pd.DataFrame) -> None:
        """Fits encoders on service name and failure type columns, incorporating defaults to prevent unseen class errors."""
        service_le = LabelEncoder()
        services = list(df["serviceName"].dropna().unique()) if "serviceName" in df.columns else []
        for default in DEFAULT_SERVICES:
            if default not in services:
                services.append(default)
        services.append("UNKNOWN")
        service_le.fit(services)
        self.encoders["service"] = service_le

        failure_le = LabelEncoder()
        failures = list(df["failureType"].dropna().unique()) if "failureType" in df.columns else []
        for default in DEFAULT_FAILURE_TYPES:
            if default not in failures:
                failures.append(default)
        failures.append("UNKNOWN")
        failure_le.fit(failures)
        self.encoders["failure_type"] = failure_le

        self.save_encoders()

    def build_feature_matrix(self, df: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """Builds a numeric feature matrix from a logs DataFrame."""
        if fit:
            self.fit_encoders(df)
        elif not self.encoders:
            if not self.load_encoders():
                logger.warning("Encoders not found on disk. Fitting on current dataset.")
                self.fit_encoders(df)

        features = []
        for _, row in df.iterrows():
            record = row.to_dict()
            features.append(self.extract_features_single(record))
        
        return np.array(features)

    def extract_features_single(self, record: Dict[str, Any]) -> np.ndarray:
        """Extracts feature vector for a single log record."""
        status_code = record.get("statusCode")
        if status_code is None:
            status_code = 0
        else:
            try:
                status_code = int(status_code)
            except (ValueError, TypeError):
                status_code = 0

        log_level = str(record.get("logLevel") or "").upper()
        is_error = 1.0 if log_level in ["ERROR", "FATAL", "WARN"] else 0.0

        service = record.get("serviceName") or "UNKNOWN"
        service_le = self.encoders.get("service")
        if service_le:
            try:
                service_encoded = float(service_le.transform([service])[0])
            except ValueError:
                service_encoded = float(service_le.transform(["UNKNOWN"])[0])
        else:
            service_encoded = 0.0

        failure_type = record.get("failureType") or "UNKNOWN"
        failure_le = self.encoders.get("failure_type")
        if failure_le:
            try:
                failure_encoded = float(failure_le.transform([failure_type])[0])
            except ValueError:
                failure_encoded = float(failure_le.transform(["UNKNOWN"])[0])
        else:
            failure_encoded = 0.0

        timestamp_str = record.get("timestamp")
        hour_of_day = 0.0
        if timestamp_str:
            try:
                dt = pd.to_datetime(timestamp_str)
                hour_of_day = float(dt.hour)
            except Exception:
                pass

        err_msg = record.get("errorMessage") or ""
        error_msg_length = float(len(err_msg))

        return np.array([
            status_code,
            is_error,
            service_encoded,
            failure_encoded,
            hour_of_day,
            error_msg_length
        ], dtype=np.float32)

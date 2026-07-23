import logging
import os
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from data_processing.log_fetcher import LogFetcher
from data_processing.feature_engineering import FeatureEngineer
from data_processing.anomaly_repository import AnomalyRepository
from anomaly_detection.models.isolation_forest_model import IsolationForestModel

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, model_dir: str = "models"):
        self.fetcher = LogFetcher()
        self.engineer = FeatureEngineer(models_dir=model_dir)
        self.model = IsolationForestModel(model_dir=model_dir)
        self.repository = AnomalyRepository()
        
        # Try to load existing model and encoders on initialization
        self.model.load()
        self.engineer.load_encoders()

    def train_from_scratch(self) -> Dict[str, Any]:
        """Fetches all parsed logs, fits encoders, trains isolation forest, and saves both."""
        df = self.fetcher.fetch_as_dataframe()
        if df.empty:
            logger.warning("No parsed logs found to train from scratch.")
            return {"status": "failed", "reason": "no data"}

        logger.info(f"Loaded {df.shape[0]} logs for training.")
        # Fit and build feature matrix
        X = self.engineer.build_feature_matrix(df, fit=True)
        self.model.train(X)

        incident_ids = [int(value) for value in df["incidentId"].dropna().tolist()] if "incidentId" in df.columns else []
        detected = self.detect_anomalies_batch(incident_ids) if incident_ids else []
        
        return {
            "status": "success",
            "samples_trained": df.shape[0],
            "results_saved": len(detected),
            "is_trained": self.model.is_trained
        }

    def detect_anomaly(self, incident_id: int) -> Dict[str, Any]:
        """Fetches log by incident_id, engineers features, and runs anomaly prediction."""
        record = self.fetcher.fetch_parsed_log_by_incident_id(incident_id)
        if not record:
            return {
                "incident_id": incident_id,
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "reason": "Incident parsed log not found in log-parser-service"
            }

        # Engineer features
        x = self.engineer.extract_features_single(record)
        is_anomaly, score, reason = self.model.predict_single(x)
        saved = self.repository.save_result(incident_id, is_anomaly, score, reason)

        return {
            "incident_id": incident_id,
            "is_anomaly": is_anomaly,
            "anomaly_score": score,
            "reason": reason,
            "id": saved["id"],
            "model_version": saved["model_version"],
            "created_at": saved["created_at"],
            "updated_at": saved["updated_at"],
        }

    def detect_anomalies_batch(self, incident_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch prediction for multiple incident IDs."""
        results = []
        # Optimization: fetch all logs first
        all_logs = self.fetcher.fetch_all_parsed_logs()
        logs_map = {log["incidentId"]: log for log in all_logs}

        records_to_predict = []
        ids_to_predict = []

        for inc_id in incident_ids:
            record = logs_map.get(inc_id)
            if not record:
                # Try fetching individually in case it's a new log
                record = self.fetcher.fetch_parsed_log_by_incident_id(inc_id)
            
            if not record:
                results.append({
                    "incident_id": inc_id,
                    "is_anomaly": False,
                    "anomaly_score": 0.0,
                    "reason": "Incident parsed log not found"
                })
            else:
                records_to_predict.append(record)
                ids_to_predict.append(inc_id)

        if records_to_predict:
            df = pd.DataFrame(records_to_predict)
            X = self.engineer.build_feature_matrix(df, fit=False)
            batch_preds = self.model.predict_batch(X)
            
            for inc_id, (is_anomaly, score, reason) in zip(ids_to_predict, batch_preds):
                saved = self.repository.save_result(inc_id, is_anomaly, score, reason)
                results.append({
                    "incident_id": inc_id,
                    "is_anomaly": is_anomaly,
                    "anomaly_score": score,
                    "reason": reason,
                    "id": saved["id"],
                    "model_version": saved["model_version"],
                    "created_at": saved["created_at"],
                    "updated_at": saved["updated_at"],
                })

        return results

    def get_results(self) -> List[Dict[str, Any]]:
        return self.repository.fetch_results()

    def get_result_by_incident_id(self, incident_id: int) -> Optional[Dict[str, Any]]:
        return self.repository.fetch_result_by_incident_id(incident_id)

    def get_status(self) -> Dict[str, Any]:
        """Returns training status of the model."""
        result_count = len(self.repository.fetch_results())
        return {
            "model_trained": self.model.is_trained,
            "encoders_loaded": bool(self.engineer.encoders),
            "contamination": self.model.contamination,
            "results_saved": result_count
        }

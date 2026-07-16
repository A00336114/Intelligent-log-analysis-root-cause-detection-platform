import logging
import pickle
import os
import numpy as np
from typing import Tuple, List
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

class IsolationForestModel:
    def __init__(self, contamination: float = 0.05, model_dir: str = "models"):
        self.contamination = contamination
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "isolation_forest.pkl")
        self.clf = IsolationForest(contamination=contamination, random_state=42)
        self.is_trained = False

    def train(self, X: np.ndarray) -> None:
        """Trains the Isolation Forest model on the provided feature matrix X."""
        if X.shape[0] < 5:
            logger.warning(f"Very small dataset for training: {X.shape[0]} rows. Using dummy fit.")
            self.clf = IsolationForest(contamination=0.01, random_state=42)
        
        logger.info(f"Training Isolation Forest model on {X.shape[0]} samples with shape {X.shape[1]}")
        self.clf.fit(X)
        self.is_trained = True
        self.save()

    def predict_single(self, x: np.ndarray) -> Tuple[bool, float, str]:
        """Predicts anomaly status, score, and reason for a single feature vector x."""
        if not self.is_trained:
            if not self.load():
                logger.warning("Model not trained and could not load from disk. Returning default (not anomaly).")
                return False, 0.0, "Model not trained"

        X_test = x.reshape(1, -1)
        pred = self.clf.predict(X_test)[0]
        is_anomaly = bool(pred == -1)

        score_sample = self.clf.score_samples(X_test)[0]
        anomaly_score = float(1.0 - (score_sample + 0.5) / 1.0)
        anomaly_score = max(0.0, min(1.0, anomaly_score))

        reason = "Normal behaviour detected"
        if is_anomaly:
            reasons = []
            if X_test[0, 1] == 1.0:
                reasons.append("high-severity error level")
            if X_test[0, 0] >= 500:
                reasons.append(f"HTTP status code {int(X_test[0, 0])}")
            if X_test[0, 5] > 500:
                reasons.append("unusually long stack trace/error message")
            
            reason = "Anomaly flagged due to: " + ", ".join(reasons) if reasons else "Statistical anomaly in log pattern"

        return is_anomaly, anomaly_score, reason

    def predict_batch(self, X: np.ndarray) -> List[Tuple[bool, float, str]]:
        """Predicts anomaly status, scores, and reasons for a batch of feature vectors X."""
        if not self.is_trained:
            if not self.load():
                logger.warning("Model not trained and could not load from disk. Returning defaults.")
                return [(False, 0.0, "Model not trained")] * X.shape[0]

        preds = self.clf.predict(X)
        scores = self.clf.score_samples(X)
        
        results = []
        for i in range(X.shape[0]):
            is_anomaly = bool(preds[i] == -1)
            anomaly_score = float(1.0 - (scores[i] + 0.5) / 1.0)
            anomaly_score = max(0.0, min(1.0, anomaly_score))
            
            reason = "Normal behaviour detected"
            if is_anomaly:
                reasons = []
                if X[i, 1] == 1.0:
                    reasons.append("high-severity error level")
                if X[i, 0] >= 500:
                    reasons.append(f"HTTP status code {int(X[i, 0])}")
                if X[i, 5] > 500:
                    reasons.append("unusually long stack trace/error message")
                reason = "Anomaly flagged due to: " + ", ".join(reasons) if reasons else "Statistical anomaly in log pattern"
                
            results.append((is_anomaly, anomaly_score, reason))
            
        return results

    def save(self) -> None:
        """Saves model to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.clf, f)
            logger.info(f"Saved Isolation Forest model to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving Isolation Forest model: {e}")

    def load(self) -> bool:
        """Loads model from disk."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.clf = pickle.load(f)
                self.is_trained = True
                logger.info(f"Loaded Isolation Forest model from {self.model_path}")
                return True
            except Exception as e:
                logger.error(f"Error loading Isolation Forest model: {e}")
        return False

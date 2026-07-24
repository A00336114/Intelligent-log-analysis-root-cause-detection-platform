import numpy as np
import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detection.models.isolation_forest_model import IsolationForestModel

def test_isolation_forest_train_and_predict():
    model = IsolationForestModel(contamination=0.1, model_dir="test_models")
    
    # Build a compact training dataset with mostly normal records and a few outliers.
    # Feature shape: 6
    np.random.seed(42)
    normal_data = np.random.normal(loc=10.0, scale=1.0, size=(50, 6))
    outlier_data = np.random.normal(loc=50.0, scale=5.0, size=(5, 6))
    X = np.vstack([normal_data, outlier_data])
    
    model.train(X)
    
    assert model.is_trained
    assert os.path.exists(model.model_path)
    
    # Predict on a normal-like point
    normal_point = np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    is_anomaly, score, reason = model.predict_single(normal_point)
    # Isolation forest should flag it as normal (False) or score it low
    assert not is_anomaly
    assert score < 0.5
    
    # Predict on a highly anomalous point
    anomalous_point = np.array([500.0, 1.0, 10.0, 10.0, 10.0, 600.0])
    is_anomaly_out, score_out, reason_out = model.predict_single(anomalous_point)
    assert is_anomaly_out
    assert score_out >= 0.5
    assert "Anomaly flagged" in reason_out
    
    # Clean up test files
    if os.path.exists(model.model_path):
        os.remove(model.model_path)
    if os.path.exists("test_models"):
        os.rmdir("test_models")

import numpy as np
import pandas as pd
import pytest
import sys
import os

# Include package root in Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing.feature_engineering import FeatureEngineer

def test_feature_engineering_extract_single():
    engineer = FeatureEngineer(models_dir="test_models")
    
    # Test record with standard values
    record = {
        "statusCode": 500,
        "logLevel": "ERROR",
        "serviceName": "payment-service",
        "failureType": "PAYMENT_BLOCKED",
        "timestamp": "2026-07-12T15:30:00Z",
        "errorMessage": "Risk check failed: limit exceeded"
    }
    
    # We haven't fit encoders yet, but extract_features_single should run gracefully returning zeros for categories
    features = engineer.extract_features_single(record)
    
    assert len(features) == 6
    assert features[0] == 500.0  # status_code
    assert features[1] == 1.0    # is_error
    assert features[4] == 15.0   # hour_of_day
    assert features[5] == len(record["errorMessage"])  # error_msg_length

def test_feature_engineering_fit_and_encode():
    engineer = FeatureEngineer(models_dir="test_models")
    
    # Sample DataFrame
    data = [
        {"statusCode": 200, "logLevel": "INFO", "serviceName": "user-service", "failureType": "UNKNOWN", "timestamp": "2026-07-12T09:00:00Z", "errorMessage": ""},
        {"statusCode": 504, "logLevel": "ERROR", "serviceName": "transaction-service", "failureType": "TIMEOUT", "timestamp": "2026-07-12T10:15:00Z", "errorMessage": "Socket timeout exception"}
    ]
    df = pd.DataFrame(data)
    
    # Build feature matrix (will fit encoders)
    X = engineer.build_feature_matrix(df, fit=True)
    
    assert X.shape == (2, 6)
    assert X[0, 0] == 200.0
    assert X[0, 1] == 0.0
    assert X[1, 0] == 504.0
    assert X[1, 1] == 1.0
    
    # Clean up test files
    if os.path.exists(engineer.encoders_path):
        os.remove(engineer.encoders_path)
    if os.path.exists("test_models"):
        os.rmdir("test_models")

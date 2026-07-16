import logging
import sys
import os

# Ensure package root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("train_cli")

from anomaly_detection.inference.anomaly_detector import AnomalyDetector

def main():
    logger.info("Initializing anomaly detector and model training...")
    detector = AnomalyDetector()
    result = detector.train_from_scratch()
    
    if result.get("status") == "success":
        logger.info(f"Model trained successfully on {result.get('samples_trained')} logs!")
    else:
        logger.error(f"Model training failed: {result.get('reason')}")
        sys.exit(1)

if __name__ == "__main__":
    main()

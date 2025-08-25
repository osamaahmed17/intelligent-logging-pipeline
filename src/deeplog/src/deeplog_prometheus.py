import redis
import torch
from deeplog import DeepLog
from preprocessor import Preprocessor
import json
import os
import pandas as pd
import numpy as np
from redis_store import push_sequence
from prometheus_client import Counter, Gauge, start_http_server
import time
import logging
import sys

# =====================
# Logging Setup (stdout)
# =====================
logger = logging.getLogger("deeplog-service")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# =====================
# Configuration
# =====================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, "deeplog_model.pth")
data_file = os.path.join(BASE_DIR, "redis_sequences.txt")
anomaly_results_file = os.path.join(BASE_DIR, "anomaly_results.txt")

# Initialize model and preprocessor
model = DeepLog(input_size=17, hidden_size=64, output_size=17).to(device)  # Adjusted for 16 unique event IDs + 1
preprocessor = Preprocessor(length=20, timeout=float('inf'))

# =====================
# Redis connection
# =====================
try:
    r = redis.Redis(host='redis.drain3.svc.cluster.local', port=6379, decode_responses=True)
    r.ping()
    logger.info("Connected to Redis")
except redis.ConnectionError as e:
    logger.error(f"Redis connection failed: {e}")
    exit(1)

# =====================
# Prometheus Metrics
# =====================
anomalies_counter = Counter("deeplog_anomalies_total", "Total detected anomalies")
normal_counter = Counter("deeplog_normal_total", "Total detected normal sequences")
last_result = Gauge("deeplog_last_result", "0=Normal,1=Anomaly")

def report_result(is_anomaly: bool):
    """Update Prometheus metrics when a sequence is classified."""
    if is_anomaly:
        anomalies_counter.inc()
        last_result.set(1)
    else:
        normal_counter.inc()
        last_result.set(0)

# =====================
# Custom Predict
# =====================
def custom_predict(model, X, y, k=2):
    """Custom prediction function to avoid buggy DeepLog.predict."""
    model.eval()
    with torch.no_grad():
        outputs = model(X)
        probabilities = torch.softmax(outputs, dim=1)
        top_k_probs, top_k_indices = torch.topk(probabilities, k, dim=1)
        logger.info(f"Predicted top-{k} indices: {top_k_indices.cpu().numpy()}, True label: {y.cpu().numpy()}")
        return top_k_indices, top_k_probs

# =====================
# Training
# =====================
def train_initial_model():
    """Train the DeepLog model on sequences from Redis."""
    logger.info("Starting training...")
    sequences = []
    try:
        while True:
            seq = r.lpop("log_sequences")
            if not seq:
                break
            try:
                parsed_seq = json.loads(seq)
                if len(parsed_seq) <= 20:
                    sequences.append(parsed_seq)
                else:
                    logger.info(f"Skipping invalid sequence length: {parsed_seq}")
            except json.JSONDecodeError as e:
                logger.info(f"JSON decode error for sequence: {seq}, error: {e}")
    except redis.RedisError as e:
        logger.erro(f"Error reading from Redis: {e}")
        return False

    if not sequences:
        logger.info("No sequences found in Redis 'log_sequences' list")
        return False

    logger.info(f"Retrieved {len(sequences)} sequences from Redis")
    
    try:
        with open(data_file, "w") as f:
            for seq in sequences:
                f.write(f"{' '.join(map(str, seq))}\n")
        logger.info(f"Saved sequences to {data_file}")
    except IOError as e:
        logger.error(f"Error writing to {data_file}: {e}")
        return False
    
    try:
        X, y, _, _ = preprocessor.text(data_file)
        X, y = X.to(device), y.to(device)
        logger.info(f"Training with {X.shape[0]} sequences, X shape: {X.shape}, y shape: {y.shape}")
        model.fit(X, y, epochs=100, batch_size=32)  # Increased epochs to 100
        torch.save(model.state_dict(), model_path)
        logger.info(f"Model trained and saved to {model_path}")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return False
    
    try:
        for seq in sequences:
            push_sequence(seq)
        logger.info("Pushed sequences back to Redis")
    except redis.RedisError as e:
        logger.error(f"Error pushing sequences to Redis: {e}")
        return False
    
    return True

# =====================
# Anomaly Detection
# =====================
def detect_anomalies():
    """Detect anomalies in sequences from Redis."""
    if not os.path.exists(model_path):
        logger.info(f"Model file {model_path} not found. Cannot detect anomalies.")
        return []

    try:
        model.load_state_dict(torch.load(model_path))
        logger.info(f"Loaded model from {model_path}")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return []

    model.eval()
    sequence_index = 250
    anomalies = []
    
    with open(anomaly_results_file, "w") as f:
        try:
            while True:
                sequence = r.lpop("log_sequences")
                logger.info(f"Popped sequence {sequence_index}: {sequence}")
                if not sequence:
                    logger.info("No more sequences in Redis. Exiting loop.")
                    break
                try:
                    seq = json.loads(sequence)
                    if len(seq) > 20:
                        logger.info(f"Skipping sequence {sequence_index} due to invalid length: {len(seq)}")
                        sequence_index += 1
                        continue
                    data_df = pd.DataFrame({
                        'timestamp': np.arange(len(seq)),
                        'event': seq,
                        'machine': [0] * len(seq)
                    })
                    X, y, _, _ = preprocessor.sequence(data_df)
                    X, y = X.to(device), y.to(device)
                    y_pred, confidence = custom_predict(model, X, y, k=2)
                    result = f"Sequence {sequence_index}: {seq} - "
                    if y[0] not in y_pred[0]:
                        result += "Anomaly\n"
                        anomalies.append((sequence_index, seq))
                        report_result(True)   # Update Prometheus
                    else:
                        result += "Normal\n"
                        report_result(False)  # Update Prometheus
                    logger.info(result.strip())
                    f.write(result)
                    sequence_index += 1
                except json.JSONDecodeError as e:
                    logger.info(f"JSON decode error for sequence {sequence_index}: {sequence}, error: {e}")
                    sequence_index += 1
                    continue
        except redis.RedisError as e:
            logger.error(f"Error reading sequences from Redis: {e}")
            return anomalies
        
        f.write("\nSummary of detected anomalies:\n")
        for idx, seq in anomalies:
            f.write(f"Sequence {idx}: {seq}\n")
    
    return anomalies

# =====================
# Continuous Monitoring
# =====================
def monitor_redis():
    """Continuously monitor Redis for new sequences."""
    if not os.path.exists(model_path):
        logger.info(f"Model file {model_path} not found. Cannot monitor Redis.")
        return

    try:
        model.load_state_dict(torch.load(model_path))
        logger.info(f"Loaded model for monitoring from {model_path}")
    except Exception as e:
        logger.info(f"Error loading model for monitoring: {e}")
        return

    model.eval()
    sequence_index = 274
    with open(anomaly_results_file, "a") as f:
        while True:
            try:
                sequence = r.lpop("log_sequences")
                logger.info(f"Monitoring - Popped sequence {sequence_index}: {sequence}")
                if sequence:
                    try:
                        seq = json.loads(sequence)
                        if len(seq) > 20:
                            logger.info(f"Skipping sequence {sequence_index} due to invalid length: {len(seq)}")
                            sequence_index += 1
                            continue
                        data_df = pd.DataFrame({
                            'timestamp': np.arange(len(seq)),
                            'event': seq,
                            'machine': [0] * len(seq)
                        })
                        X, y, _, _ = preprocessor.sequence(data_df)
                        X, y = X.to(device), y.to(device)
                        y_pred, confidence = custom_predict(model, X, y, k=2)
                        result = f"Sequence {sequence_index}: {seq} - "
                        if y[0] not in y_pred[0]:
                            result += "Anomaly\n"
                            report_result(True)
                        else:
                            result += "Normal\n"
                            report_result(False)
                        logger.info(result.strip())
                        f.write(result)
                        sequence_index += 1
                    except json.JSONDecodeError as e:
                        logger.info(f"JSON decode error for sequence {sequence_index}: {sequence}, error: {e}")
                        sequence_index += 1
                        continue
                else:
                    logger.info("No new sequences. Sleeping for 15 seconds.")
                    time.sleep(15)
            except redis.RedisError as e:
                logger.info(f"Error during monitoring: {e}")
                time.sleep(15)

# =====================
# Main Entry
# =====================
if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8000)  # Exposes metrics at http://localhost:8000/metrics
    
    if not os.path.exists(model_path) or os.path.getsize(model_path) == 0:
        success = train_initial_model()
        if not success:
            logger.info("Training failed. Exiting.")
            exit(1)

    anomalies = detect_anomalies()
    logger.info("\nSummary of detected anomalies:")
    for idx, seq in anomalies:
        logger.info(f"Sequence {idx}: {seq}")
    
    logger.info("\nStarting continuous monitoring...")
    monitor_redis()

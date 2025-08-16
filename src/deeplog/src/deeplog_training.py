import redis
import torch
from deeplog import DeepLog
from preprocessor import Preprocessor
import json
import os
import pandas as pd
import numpy as np
from redis_store import push_sequence

# Configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, "deeplog_model.pth")
data_file = os.path.join(BASE_DIR, "redis_sequences.txt")
anomaly_results_file = os.path.join(BASE_DIR, "anomaly_results.txt")

# Initialize model and preprocessor
model = DeepLog(input_size=17, hidden_size=64, output_size=17).to(device)  # Adjusted for 16 unique event IDs + 1
preprocessor = Preprocessor(length=20, timeout=float('inf'))

# Redis connection
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("Connected to Redis")
except redis.ConnectionError as e:
    print(f"Redis connection failed: {e}")
    exit(1)

def custom_predict(model, X, y, k=2):  # Changed k=1 to k=2 for broader prediction
    """Custom prediction function to avoid buggy DeepLog.predict."""
    model.eval()
    with torch.no_grad():
        outputs = model(X)
        probabilities = torch.softmax(outputs, dim=1)
        top_k_probs, top_k_indices = torch.topk(probabilities, k, dim=1)
        print(f"Predicted top-{k} indices: {top_k_indices.cpu().numpy()}, True label: {y.cpu().numpy()}")
        return top_k_indices, top_k_probs

def train_initial_model():
    """Train the DeepLog model on sequences from Redis."""
    print("Starting training...")
    sequences = []
    try:
        while True:
            seq = r.lpop("log_sequences")
            if not seq:
                break
            try:
                parsed_seq = json.loads(seq)
                if len(parsed_seq) == 20:
                    sequences.append(parsed_seq)
                else:
                    print(f"Skipping invalid sequence length: {parsed_seq}")
            except json.JSONDecodeError as e:
                print(f"JSON decode error for sequence: {seq}, error: {e}")
    except redis.RedisError as e:
        print(f"Error reading from Redis: {e}")
        return False

    if not sequences:
        print("No sequences found in Redis 'log_sequences' list")
        return False

    print(f"Retrieved {len(sequences)} sequences from Redis")
    
    try:
        with open(data_file, "w") as f:
            for seq in sequences:
                f.write(f"{' '.join(map(str, seq))}\n")
        print(f"Saved sequences to {data_file}")
    except IOError as e:
        print(f"Error writing to {data_file}: {e}")
        return False
    
    try:
        X, y, _, _ = preprocessor.text(data_file)
        X, y = X.to(device), y.to(device)
        print(f"Training with {X.shape[0]} sequences, X shape: {X.shape}, y shape: {y.shape}")
        model.fit(X, y, epochs=100, batch_size=32)  # Increased epochs to 100
        torch.save(model.state_dict(), model_path)
        print(f"Model trained and saved to {model_path}")
    except Exception as e:
        print(f"Training failed: {e}")
        return False
    
    try:
        for seq in sequences:
            push_sequence(seq)
        print("Pushed sequences back to Redis")
    except redis.RedisError as e:
        print(f"Error pushing sequences to Redis: {e}")
        return False
    
    return True

def detect_anomalies():
    """Detect anomalies in sequences from Redis."""
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found. Cannot detect anomalies.")
        return []

    try:
        model.load_state_dict(torch.load(model_path))
        print(f"Loaded model from {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        return []

    model.eval()
    sequence_index = 250
    anomalies = []
    
    with open(anomaly_results_file, "w") as f:
        try:
            while True:
                sequence = r.lpop("log_sequences")
                print(f"Popped sequence {sequence_index}: {sequence}")
                if not sequence:
                    print("No more sequences in Redis. Exiting loop.")
                    break
                try:
                    seq = json.loads(sequence)
                    if len(seq) != 20:
                        print(f"Skipping sequence {sequence_index} due to invalid length: {len(seq)}")
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
                    else:
                        result += "Normal\n"
                    print(result.strip())
                    f.write(result)
                    sequence_index += 1
                except json.JSONDecodeError as e:
                    print(f"JSON decode error for sequence {sequence_index}: {sequence}, error: {e}")
                    sequence_index += 1
                    continue
        except redis.RedisError as e:
            print(f"Error reading sequences from Redis: {e}")
            return anomalies
        
        f.write("\nSummary of detected anomalies:\n")
        for idx, seq in anomalies:
            f.write(f"Sequence {idx}: {seq}\n")
    
    normal_count = sequence_index - 250 - len(anomalies)
    anomaly_count = len(anomalies)
    print("""
```chartjs
{
  "type": "bar",
  "data": {
    "labels": ["Normal", "Anomalous"],
    "datasets": [{
      "label": "Sequence Counts",
      "data": [%d, %d],
      "backgroundColor": ["#36A2EB", "#FF6384"],
      "borderColor": ["#36A2EB", "#FF6384"],
      "borderWidth": 1
    }]
  },
  "options": {
    "scales": {
      "y": { "beginAtZero": true, "title": { "display": true, "text": "Number of Sequences" } },
      "x": { "title": { "display": true, "text": "Sequence Type" } }
    },
    "plugins": { "title": { "display": true, "text": "DeepLog Anomaly Detection Results" } }
  }
}
```""" % (normal_count, anomaly_count))
    
    return anomalies

def monitor_redis():
    """Continuously monitor Redis for new sequences."""
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found. Cannot monitor Redis.")
        return

    try:
        model.load_state_dict(torch.load(model_path))
        print(f"Loaded model for monitoring from {model_path}")
    except Exception as e:
        print(f"Error loading model for monitoring: {e}")
        return

    model.eval()
    sequence_index = 274
    with open(anomaly_results_file, "a") as f:
        while True:
            try:
                sequence = r.lpop("log_sequences")
                print(f"Monitoring - Popped sequence {sequence_index}: {sequence}")
                if sequence:
                    try:
                        seq = json.loads(sequence)
                        if len(seq) != 20:
                            print(f"Skipping sequence {sequence_index} due to invalid length: {len(seq)}")
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
                        else:
                            result += "Normal\n"
                        print(result.strip())
                        f.write(result)
                        sequence_index += 1
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error for sequence {sequence_index}: {sequence}, error: {e}")
                        sequence_index += 1
                        continue
                else:
                    print("No new sequences. Sleeping for 15 seconds.")
                    import time
                    time.sleep(15)
            except redis.RedisError as e:
                print(f"Error during monitoring: {e}")
                time.sleep(15)

if __name__ == "__main__":
   
    if not os.path.exists(model_path) or os.path.getsize(model_path) == 0:
        success = train_initial_model()
        if not success:
            print("Training failed. Exiting.")
            exit(1)

    anomalies = detect_anomalies()
    print("\nSummary of detected anomalies:")
    for idx, seq in anomalies:
        print(f"Sequence {idx}: {seq}")
    
   
    print("\nStarting continuous monitoring...")
    monitor_redis()


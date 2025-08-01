# import subprocess
# import json
# import logging
# from drain3 import TemplateMiner
# from drain3.template_miner_config import TemplateMinerConfig
# from drain3.file_persistence import FilePersistence

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger(__name__)

# # Configuration
# LOKI_URL = "http://localhost:3100"
# QUERY = '{namespace="npps"}'
# DRAIN3_PERSISTENCE_FILE = "./drain3_state.bin"

# def query_loki():
#     """Query logs from Loki using logcli and jq."""
#     cmd = (
#         f'logcli --addr="{LOKI_URL}" query \'{QUERY}\' '
#         '--limit=5 --output jsonl | jq -r \'select(.line | startswith("{")) | .line | fromjson | .log\''
#     )
#     try:
#         result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
#         log_lines = result.stdout.strip().split('\n')
#         return [line for line in log_lines if line]  # Filter out empty lines
#     except subprocess.CalledProcessError as e:
#         logger.error(f"Error querying Loki: {e.stderr}")
#         return []

# def process_with_drain3(log_lines):
#     """Process logs with Drain3 and extract templates."""
#     persistence = FilePersistence(DRAIN3_PERSISTENCE_FILE)
#     config = TemplateMinerConfig()
#     config.load("./drain3.ini")
#     template_miner = TemplateMiner(persistence, config)

#     logger.info(f"Drain3 started with 'FILE' persistence")
#     for log_line in log_lines:
#         result = template_miner.add_log_message(log_line)
#         logger.info(json.dumps(result))
#         params = template_miner.extract_parameters(result["template_mined"], log_line)
#         logger.info(f"Parameters: {params}")

#     logger.info("Mined clusters:")
#     for cluster in template_miner.drain.clusters:
#         logger.info(f"ID={cluster.cluster_id} : size={cluster.size} : {cluster.get_template()}")

# if __name__ == "__main__":
#     log_lines = query_loki()
#     if log_lines:
#         process_with_drain3(log_lines)
#     else:
#         logger.info("No logs retrieved from Loki")




import subprocess
import json
import re
import logging
import os
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence
from redis_store import push_sequence

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Configuration from environment variables
LOKI_URL = os.getenv("LOKI_URL", "http://loki.monitoring.svc.cluster.local:3100")
QUERY = os.getenv("LOKI_QUERY", '{namespace="npps"}')
LIMIT = os.getenv("LOKI_LIMIT", "20")
OUTPUT_FORMAT = os.getenv("LOKI_OUTPUT_FORMAT", "jsonl")
JQ_FILTER = os.getenv("JQ_FILTER", 'select(.line | startswith("{")) | .line | fromjson | .log')
DRAIN3_PERSISTENCE_FILE = "./drain3_state.bin"
DRAIN3_CONFIG_FILE = "./drain3.ini"  # or /app/drain3.ini in Docker

# Regex to remove timestamps from beginning of log lines
TIMESTAMP_REGEX = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+'

def query_loki():
    """Query logs from Loki using logcli and jq."""
    cmd = (
        f'logcli --addr="{LOKI_URL}" query \'{QUERY}\' '
        f'--limit={LIMIT} --output {OUTPUT_FORMAT} | jq -r \'{JQ_FILTER}\''
    )
    logger.info(f"Executing logcli command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        log_lines = result.stdout.strip().split('\n')
        return [line for line in log_lines if line]
    except subprocess.CalledProcessError as e:
        logger.error(f"Error querying Loki: {e.stderr}")
        return []

def preprocess_log_line(log_line):
    """Remove timestamp prefix from log line."""
    return re.sub(TIMESTAMP_REGEX, '', log_line).strip()

def process_with_drain3(log_lines):
    """Process logs with Drain3, extract cluster IDs, and send each one to Redis."""
    persistence = FilePersistence(DRAIN3_PERSISTENCE_FILE)
    config = TemplateMinerConfig()
    config.load(DRAIN3_CONFIG_FILE)
    template_miner = TemplateMiner(persistence, config)

    logger.info(f"Drain3 started with 'FILE' persistence")

    for log_line in log_lines:
        cleaned_log_line = preprocess_log_line(log_line)
        if not cleaned_log_line:
            logger.warning(f"Skipping empty log line after preprocessing: {log_line}")
            continue

        result = template_miner.add_log_message(cleaned_log_line)
        if result is None:
            continue

        cluster_id = result["cluster_id"]
        logger.info(f"Cluster ID: {cluster_id}")

        # Push this single cluster ID to Redis
        push_sequence([cluster_id])

        params = template_miner.extract_parameters(result["template_mined"], cleaned_log_line)
        logger.info(f"Parameters: {params}")

    logger.info("Mined clusters:")
    for cluster in template_miner.drain.clusters:
        logger.info(f"ID={cluster.cluster_id} : size={cluster.size} : {cluster.get_template()}")

if __name__ == "__main__":
    log_lines = query_loki()
    if log_lines:
        process_with_drain3(log_lines)
    else:
        logger.info("No logs retrieved from Loki")


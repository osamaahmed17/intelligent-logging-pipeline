import subprocess
import json
import logging
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Configuration
LOKI_URL = "http://localhost:3100"
QUERY = '{namespace="npps"}'
DRAIN3_PERSISTENCE_FILE = "./drain3_state.bin"

def query_loki():
    """Query logs from Loki using logcli and jq."""
    cmd = (
        f'logcli --addr="{LOKI_URL}" query \'{QUERY}\' '
        '--limit=5 --output jsonl | jq -r \'select(.line | startswith("{")) | .line | fromjson | .log\''
    )
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        log_lines = result.stdout.strip().split('\n')
        return [line for line in log_lines if line]  # Filter out empty lines
    except subprocess.CalledProcessError as e:
        logger.error(f"Error querying Loki: {e.stderr}")
        return []

def process_with_drain3(log_lines):
    """Process logs with Drain3 and extract templates."""
    persistence = FilePersistence(DRAIN3_PERSISTENCE_FILE)
    config = TemplateMinerConfig()
    config.load("./drain3.ini")
    template_miner = TemplateMiner(persistence, config)

    logger.info(f"Drain3 started with 'FILE' persistence")
    for log_line in log_lines:
        result = template_miner.add_log_message(log_line)
        logger.info(json.dumps(result))
        params = template_miner.extract_parameters(result["template_mined"], log_line)
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

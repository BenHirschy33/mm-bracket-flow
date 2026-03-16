import os
import json
import time
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MANAGER - %(message)s',
    handlers=[
        logging.FileHandler("docs/swarm_heartbeat.log"),
        logging.StreamHandler()
    ]
)

PROJECT_ROOT = "/Users/benhirschy/Desktop/MM-Bracket-Flow"
SYNC_FILE = os.path.join(PROJECT_ROOT, "docs/agent_sync.json")
POLL_INTERVAL = 300 # 5 minutes

AGENT_STATUS_FILES = {
    "research": "../MM-Research/docs/research_status.txt",
    "optimization": "../MM-Optimization/docs/optimization_status.txt",
    "web": "../MM-Web/docs/web_status.txt"
}

SILENCE_THRESHOLD = 600 # 10 minutes (2 polling cycles)
last_activity_time = {k: time.time() for k in AGENT_STATUS_FILES.keys()}

def load_sync():
    try:
        with open(SYNC_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_sync(data):
    with open(SYNC_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def monitor_loop(duration_hours=2):
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)
    
    logging.info(f"MANAGER ACTIVE: Monitoring Swarm for {duration_hours} hours...")
    
    while time.time() < end_time:
        sync_data = load_sync()
        dirty = False
        
        for agent, path in AGENT_STATUS_FILES.items():
            abs_path = os.path.join(PROJECT_ROOT, path)
            if os.path.exists(abs_path):
                with open(abs_path, 'r') as f:
                    content = f.read().strip()
                    if content and sync_data.get(agent, {}).get("status") != content:
                        logging.info(f"SYNC UP: {agent} reporting activity: {content[:50]}...")
                        if agent not in sync_data: sync_data[agent] = {}
                        sync_data[agent]["status"] = content
                        sync_data[agent]["last_check"] = time.ctime()
                        dirty = True
        
        if dirty:
            save_sync(sync_data)
            logging.info("Heartbeat: agent_sync.json updated.")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    monitor_loop()

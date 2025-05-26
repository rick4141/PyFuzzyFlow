import os
import json
from datetime import datetime

class ExecutionLogger:
    def __init__(self, log_dir="logs", run_id=None):
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.run_id = run_id or now
        self.base_dir = os.path.join(log_dir, f"run_{self.run_id}")
        os.makedirs(self.base_dir, exist_ok=True)
        self.log_file = os.path.join(self.base_dir, f"run_{self.run_id}.log")
        self.f = open(self.log_file, 'a')

    def log(self, data):
        line = f"{datetime.now().isoformat()} | {json.dumps(data, default=str)}"
        self.f.write(line + '\n')
        self.f.flush()

    def close(self):
        self.f.close()

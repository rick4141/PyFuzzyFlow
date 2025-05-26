# modules/utils.py

import shutil
import subprocess
import re
import platform
import json
from modules.system_metrics import SystemMetrics

WHITELIST = [
    "ls", "cat", "echo", "pwd", "whoami", "uname", "date", "df", "free", "python3", "pip", "ps", "id"
]
DANGEROUS = [
    "rm", "sudo", "shutdown", "reboot", "mkfs", "dd", "kill", "passwd", "chown", "chmod", "init", "telinit"
]

def command_exists(cmd):
    first = cmd.split()[0]
    return shutil.which(first) is not None

def check_command_safety(cmd):
    for bad in DANGEROUS:
        if bad in cmd:
            print(f"[WARNING] Command '{cmd}' is considered dangerous! Not in whitelist.")
            return False
    if WHITELIST and cmd.split()[0] not in WHITELIST:
        print(f"[INFO] Command '{cmd}' is NOT in the safe WHITELIST. Use with caution.")
    return True

def build_metric_func(step):
    """
    Given a step dictionary, returns a callable for the metric.
    Supports custom_shell and all SystemMetrics.
    """
    metric_func_name = step.get("metric_func")
    if not metric_func_name:
        raise ValueError("No 'metric_func' specified in step.")
    if metric_func_name == "custom_shell":
        cmd = step.get("custom_command")
        regex = step.get("parse_regex")
        formula = step.get("parse_formula", "float(match.group(1))")
        if not cmd:
            raise ValueError("Missing 'custom_command' in custom_shell step.")
        def custom_metric():
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                if result.returncode != 0:
                    return -1
                if regex:
                    match = re.search(regex, result.stdout)
                    if match:
                        return eval(formula)
                    else:
                        return -1
                else:
                    try:
                        return float(result.stdout.strip())
                    except Exception:
                        return -1
            except Exception:
                return -1
        return custom_metric
    else:
        try:
            return SystemMetrics.get_metric_func(metric_func_name)
        except KeyError:
            raise ValueError(f"Metric '{metric_func_name}' is not available. Use --list-metrics to see available ones.")

def list_available_metrics():
    print("Available metrics (built-in and custom):")
    for m in sorted(SystemMetrics.list_metrics()):
        print(f"  - {m}")

def generate_example_testcase(filename=None):
    sysname = platform.system().lower()
    example = {
        "name": "Example Pipeline",
        "min_passed": 1,
        "steps": [
            {
                "description": "Check Python version",
                "type": "shell",
                "command": "python3 --version",
                "eval_contains": "Python",
                "required": True,
                "retries": 1
            },
            {
                "description": "Fuzzy CPU load",
                "type": "fuzzy",
                "metric_func": "cpu_percent",
                "thresholds": [10, 50, 80],
                "eval_label": "LOW",
                "duration": 3,
                "required": True,
                "retries": 1
            }
        ]
    }
    fname = filename or f"testcases/example_{sysname}.json"
    with open(fname, "w") as f:
        json.dump(example, f, indent=2)
    print(f"[INFO] Example testcase saved to {fname}")

# Allow adding new metrics from CLI (for --add-metric)
def register_cli_metric(name, command):
    """
    Registers a new metric in SystemMetrics class using a shell command.
    """
    def custom_metric():
        try:
            out = subprocess.check_output(command, shell=True, text=True)
            return float(out.strip().split()[0])
        except Exception as e:
            print(f"[ERROR] Custom metric '{name}': {e}")
            return -1
    SystemMetrics.register_metric(name, custom_metric)
    print(f"[INFO] Custom metric '{name}' registered.")


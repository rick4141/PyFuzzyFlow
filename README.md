# PyFuzzyFlow Industrial Fuzzy Test Pipeline Runner

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Fuzzy Logic: Theory and Implementation](#fuzzy-logic-theory-and-implementation)
- [Neuro-Fuzzy Option](#neuro-fuzzy-option)
- [Usage](#usage)
  - [Installation](#installation)
  - [Basic Commands](#basic-commands)
  - [Adding Custom Metrics](#adding-custom-metrics)
  - [Generating Example Testcases](#generating-example-testcases)
  - [Running a Test Pipeline](#running-a-test-pipeline)
- [Testcase Format](#testcase-format)
  - [Example Testcases](#example-testcases)
  - [Industry Example Pipeline](#industry-example-pipeline)
- [Advanced: How to Add Your Own Metrics](#advanced-how-to-add-your-own-metrics)
- [Theory: Fuzzy Logic Deep Dive](#theory-fuzzy-logic-deep-dive)
- [FAQ and Best Practices](#faq-and-best-practices)
- [Appendix: Troubleshooting](#appendix-troubleshooting)

---

## Introduction

**PyFuzzyFlow** is an open-source, extensible test automation pipeline for industrial system validation using fuzzy logic and neuro-fuzzy (experimental) approaches.  
It is designed to evaluate health checks and system status through classic or adaptive fuzzy classification, with robust reporting and custom metric integration.

---

## Features

- Fuzzy logic-based step evaluation (classic or neuro-fuzzy)
- Step-by-step pipeline definition in JSON format
- Automatic logging and reporting to Excel/HTML
- Dynamic metric registration (add shell or Python-based metrics at runtime)
- Safe command whitelist & warnings for shell steps
- Flexible retries, failure hooks, and dry-run support
- System metrics introspection (CPU, RAM, disk, network, etc)
- Example and industry-oriented test cases included

---

## Architecture Overview

**Main components:**
- `main.py` – Pipeline runner, argparser, control flow
- `modules/fuzzy_validator.py` – Fuzzy (and neuro-fuzzy) step evaluation
- `modules/system_metrics.py` – Built-in and custom metric registry
- `modules/utils.py` – Helpers: command safety, metric registration, test generation
- `modules/logger.py`, `modules/reporting.py` – Logging, Excel/HTML reporting
- **Testcases** – JSON definitions in `test_case_examples/`

---

## Fuzzy Logic: Theory and Implementation

Fuzzy logic allows classification of real-world values (like CPU %, RAM usage) into human-like categories (“LOW”, “MED”, “HIGH”), with degrees of membership rather than binary thresholds.

- **Membership functions:** Typically trapezoidal, mapping values to a range [0, 1] for each class.
- **Adaptive thresholds:** PyFuzzyFlow can update thresholds dynamically based on data percentiles.
- **Label assignment:** The system selects the category with the highest membership value, but all memberships are logged for transparency.

See the [Theory](#theory-fuzzy-logic-deep-dive) section for a detailed explanation.

---

## Neuro-Fuzzy Option

Neuro-fuzzy steps (experimental) can be used by setting `"mode": "neuro-fuzzy"` or type `"neuro_fuzzy"`.  
This mode simulates adaptive learning and can be extended to use real neuro-fuzzy (ANFIS) models in the future.  
Currently, the system provides random softmax-style outputs to emulate this logic for demonstration/testing.

---

## Usage

### Installation

Install requirements:
```bash
pip install -r requirements.txt
```

Requirements include: psutil, scikit-fuzzy, numpy, openpyxl, pandas.

Ensure you are in the root folder (PyFuzzyFlow/).

Basic Commands
List available metrics:

```bash
python main.py --list-metrics
```

Run a pipeline:
```bash
python main.py --testcase test_case_examples/test_case_ultimate.json --logdir logs --interval 1
```

Dry-run (show steps without running):
```bash
python main.py --testcase test_case_examples/test_case_ultimate.json --dry-run
```

Run a single step:
```bash
python main.py --testcase test_case_examples/test_case_ultimate.json --step 2
```

Adding Custom Metrics
You can add a new metric at runtime (shell-based):

```bash
python main.py --add-metric mem_avail_gb "python3 -c 'import psutil; print(psutil.virtual_memory().available / (1024**3))'"
```

The metric will be available for the current run and visible in --list-metrics.

Add the metric name (mem_avail_gb) in your testcase under "metric_func".

Generating Example Testcases

```bash
python main.py --generate-example
```

This creates an example testcase JSON for your system.

### Running a Test Pipeline
See Testcase Format and Example Testcases for details.

### Testcase Format
Each testcase is a JSON file, for example:

```bash
{
  "name": "Sanity Healthcheck Pipeline",
  "min_passed": 2,
  "steps": [
    {
      "description": "Check Python version",
      "type": "shell",
      "command": "python3 --version",
      "eval_contains": "Python",
      "required": true
    },
    {
      "description": "Fuzzy CPU Usage",
      "type": "fuzzy",
      "metric_func": "cpu_percent",
      "thresholds": [10, 30, 70],
      "duration": 2,
      "eval_label": "LOW"
    }
  ]
}

```

Key fields: 

- "description": Human-readable step label.

- "type": "shell", "boolean", "fuzzy", "neuro_fuzzy".

- "command" or "metric_func": What to run.

- "thresholds", "duration", "eval_label": For fuzzy steps.

- "required", "retries", "on_fail": Step control.

### Example Testcases
test_case_examples/test_case_ultimate.json

```bash
{
  "name": "Industry Sanity Healthcheck Pipeline",
  "min_passed": 3,
  "steps": [
    {
      "description": "Check Docker Service Status",
      "type": "shell",
      "command": "systemctl is-active docker || echo 'inactive'",
      "eval_contains": "active",
      "required": false
    },
    {
      "description": "Fuzzy CPU Usage Check",
      "type": "fuzzy",
      "metric_func": "cpu_percent",
      "thresholds": [10, 30, 70],
      "label_names": ["LOW", "MED", "HIGH"],
      "duration": 3,
      "eval_label": "LOW",
      "required": true
    },
    {
      "description": "Fuzzy RAM Percent Usage",
      "type": "fuzzy",
      "metric_func": "ram_percent",
      "thresholds": [30, 60, 85],
      "label_names": ["LOW", "MED", "HIGH"],
      "duration": 3,
      "eval_label": "LOW",
      "required": true
    },
    {
      "description": "Neuro-Fuzzy Free Memory (GB)",
      "type": "neuro_fuzzy",
      "metric_func": "mem_avail_gb",
      "thresholds": [2, 4, 8],
      "label_names": ["LOW", "MED", "HIGH"],
      "duration": 2,
      "eval_label": "HIGH",
      "required": false
    },
    {
      "description": "Disk Usage on /",
      "type": "fuzzy",
      "metric_func": "disk_percent",
      "thresholds": [50, 80, 95],
      "label_names": ["LOW", "MED", "HIGH"],
      "duration": 1,
      "eval_label": "LOW",
      "required": true
    }
  ]
}

```

### Industry Example Pipeline
A typical industrial healthcheck might include:

- Service status (e.g., Docker, PostgreSQL)

- CPU, RAM, and Disk health (fuzzy)

- Optional network throughput checks

- Custom business KPIs (number of running processes, DB connections, etc.)


Theory: Fuzzy Logic Deep Dive
Fuzzy logic is a mathematical framework for dealing with uncertainty and gradual change, as opposed to binary logic.
It allows you to design systems that reason with degrees of membership, rather than crisp cutoffs.

Why Fuzzy?
Many physical systems don’t have clear boundaries. “Is it hot?” is fuzzy, not crisp.

Membership functions allow smooth, interpretable transitions.

Useful for health checks, automation, and industrial systems.

Membership Functions
A membership function maps a numeric value (e.g., CPU %) to a degree of belonging in each fuzzy set (LOW, MED, HIGH).
The most common functions are triangular or trapezoidal.

Example (for “cpu_percent”):

LOW: 0–15%

MED: 10–50%

HIGH: 40–100%

Each actual value may partially belong to several sets:

22% CPU: LOW = 0.2, MED = 0.8, HIGH = 0.0

Adaptive Thresholds
Instead of static ranges, PyFuzzyFlow can update these thresholds using percentiles from recent data, making your logic robust to changing environments.

Label Assignment
The class with the highest membership is chosen as the label, but you can also review all degrees in logs/reports.

### FAQ and Best Practices
Q: Why are some shell commands skipped?
A: The runner checks command existence and safety. Some system commands may not be available, especially on macOS vs Linux.

Q: Can I use neuro-fuzzy for real neural learning?
A: Yes, but you’ll need to plug in a real ANFIS or similar library. The current version provides a mock softmax as proof-of-concept.

Q: How should I design thresholds?
A: Use domain knowledge, or let the system adapt via percentiles. Always monitor with logs/ and tune as needed.

Q: How do I add a test step that only runs if another fails?
A: Use "on_fail" in your step JSON to trigger a recovery or diagnostic command.

Appendix: Troubleshooting
FileNotFoundError: Ensure your testcase path is correct.

Metric not available: Add it via --add-metric or edit system_metrics.py.

Shell commands on macOS: Some Linux commands (systemctl, free) may not exist on macOS. Use appropriate equivalents.


PyFuzzyFlow is ready for industrial extension, CI integration, and monitoring.
Feel free to fork, contribute, or request advanced examples!


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


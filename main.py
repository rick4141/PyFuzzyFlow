import argparse
import json
import time
from datetime import datetime
import os
import hashlib

from modules.fuzzy_validator import FuzzyValidator
from modules.logger import ExecutionLogger
from modules.system_metrics import get_extended_system_info
from modules.utils import (
    command_exists,
    build_metric_func,
    list_available_metrics,
    generate_example_testcase,
    check_command_safety,
    register_cli_metric
)
from modules.reporting import export_log_to_excel, export_log_to_html

def evaluate_shell(output, eval_contains):
    if eval_contains and eval_contains in output:
        return True
    elif eval_contains:
        return False
    else:
        return None

def evaluate_fuzzy(all_labels, eval_label):
    return eval_label in all_labels if eval_label else None

def main():
    parser = argparse.ArgumentParser(description="Industrial Fuzzy Test Pipeline Runner")
    parser.add_argument("--testcase", type=str, required=False, help="Path to test_case.json")
    parser.add_argument("--logdir", type=str, default="logs", help="Log directory")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between fuzzy samples (seconds)")
    parser.add_argument("--list-metrics", action="store_true", help="List all available metrics and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show pipeline steps without executing")
    parser.add_argument("--step", type=int, help="Run only step N (1-based)")
    parser.add_argument("--generate-example", action="store_true", help="Generate an example testcase and exit")
    parser.add_argument("--add-metric", nargs=2, metavar=('NAME', 'COMMAND'), help="Register a new shell-based metric: NAME COMMAND")
    args = parser.parse_args()

    if args.add_metric:
        name, command = args.add_metric
        register_cli_metric(name, command)

    if args.generate_example:
        generate_example_testcase()
        return

    if args.list_metrics:
        list_available_metrics()
        return

    if not args.testcase:
        print("ERROR: --testcase argument is required unless --list-metrics or --generate-example is used.")
        return

    with open(args.testcase) as f:
        test_case = json.load(f)

    if args.dry_run:
        print("\n[DRY-RUN] Steps to execute:")
        for idx, step in enumerate(test_case.get("steps", [])):
            print(f"[{idx+1}] {step.get('description')} (type: {step.get('type')})")
        return

    steps = test_case.get("steps", [])
    if args.step:
        idx = args.step - 1
        if idx < 0 or idx >= len(steps):
            print(f"Invalid --step {args.step}, there are only {len(steps)} steps.")
            return
        steps = [steps[idx]]

    # --- Pre-Validation: check for missing commands and whitelist ---
    for step in steps:
        typ = step.get("type")
        if typ in ["boolean", "shell"]:
            cmd = step.get("command")
            if not cmd or not command_exists(cmd):
                print(f"[WARNING] Command '{cmd}' not found for step '{step.get('description')}'. Step will be skipped.")
                step['skip'] = True
            else:
                check_command_safety(cmd)
        elif typ == "fuzzy" and step.get("metric_func") == "custom_shell":
            cmd = step.get("custom_command")
            if not cmd or not command_exists(cmd):
                print(f"[WARNING] Custom shell command '{cmd}' not found for step '{step.get('description')}'. Step will be skipped.")
                step['skip'] = True
            else:
                check_command_safety(cmd)

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(args.logdir, f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    logger = ExecutionLogger(log_dir=args.logdir, run_id=run_id)
    print(f"\n=== Running Pipeline: {test_case.get('name', '')} ===\n")

    # --- Extended system info ---
    sysinfo = get_extended_system_info()
    run_hash = hashlib.sha256((test_case.get("name", "") + datetime.now().isoformat()).encode()).hexdigest()[:10]
    logger.log({"event": "run_id", "run_id": run_hash})

    logger.log({
        "event": "start_pipeline",
        "test_case": test_case.get("name", ""),
        "start_time": datetime.now().isoformat(),
        "system_info": sysinfo,
        "metadata": test_case.get("metadata", {})
    })

    pipeline_eval_summary = []

    for idx, step in enumerate(steps):
        if step.get("skip"):
            print(f"[SKIPPED] Step '{step.get('description')}' skipped due to missing command.")
            logger.log({"step": step.get('description'), "eval": "[SKIPPED]", "reason": "missing command"})
            continue

        desc = step.get("description", f"Step {idx+1}")
        typ = step.get("type", "shell")
        required = step.get("required", True)
        retries = step.get("retries", 1)
        attempt = 0
        passed = False

        logger.log({"step": desc, "type": typ, "timestamp": datetime.now().isoformat(), "required": required})

        print(f"\n[STEP {idx+1}] {desc}")

        while attempt < retries:
            attempt += 1
            try:
                if typ == "shell":
                    import subprocess
                    cmd = step["command"]
                    check_command_safety(cmd)
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    output = result.stdout.strip() + "\n" + result.stderr.strip()
                    logger.log({
                        "step": desc,
                        "command": cmd,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    })
                    print(output)
                    eval_contains = step.get("eval_contains", "")
                    eval_result = evaluate_shell(output, eval_contains)
                    passed = eval_result is True
                    if passed:
                        tag = "[EVAL][PASSED]"
                        print(f"{tag} '{eval_contains}' found in output.")
                    elif eval_result is False:
                        tag = "[EVAL][FAILED]"
                        print(f"{tag} '{eval_contains}' NOT found in output.")
                    else:
                        tag = "[EVAL][SKIPPED]"
                        print(tag)
                    logger.log({"step": desc, "eval": tag})
                    break

                elif typ == "boolean":
                    import subprocess
                    cmd = step["command"]
                    check_command_safety(cmd)
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    passed = result.returncode == 0
                    tag = "[EVAL][PASSED]" if passed else "[EVAL][FAILED]"
                    print(f"{tag} Command returned code {result.returncode}")
                    logger.log({
                        "step": desc,
                        "command": cmd,
                        "returncode": result.returncode,
                        "eval": tag
                    })
                    if passed:
                        break

                elif typ == "fuzzy" or typ == "neuro_fuzzy":
                    # Detect mode: use step["mode"], or infer from type
                    fuzzy_mode = step.get("mode")
                    if not fuzzy_mode:
                        fuzzy_mode = "classic" if typ == "fuzzy" else "neuro-fuzzy"

                    validator = FuzzyValidator(
                        metric_func=build_metric_func(step),
                        thresholds=step.get("thresholds", [10, 30, 70]),
                        min_thresholds=step.get("min_thresholds", [10, 30, 70]),
                        history_size=step.get("history_size", 10),
                        update_every=step.get("update_every", 2),
                        label_names=step.get("label_names", ["LOW", "MED", "HIGH"]),
                        mode=fuzzy_mode
                    )

                    duration = int(step.get("duration", 5))
                    eval_label = step.get("eval_label")
                    all_labels = []
                    print(f"Fuzzy validation on {step.get('metric_func')} for {duration}s (mode: {fuzzy_mode})")
                    end = time.time() + duration
                    while time.time() < end:
                        value, label, vals = validator.validate()
                        all_labels.append(label)
                        logger.log({
                            "step": desc,
                            "metric": step.get('metric_func'),
                            "value": value,
                            "label": label,
                            "fuzzy": vals
                        })
                        print(f"{step.get('metric_func')}: {value:.1f} | {label} | {vals}")
                        time.sleep(args.interval)
                        if value == -1:
                            print(f"[WARNING] {desc} metric could not be evaluated. Is the device and command present?")
                    passed = evaluate_fuzzy(all_labels, eval_label)
                    tag = "[EVAL][PASSED]" if passed else "[EVAL][FAILED]"
                    msg = f"Label '{eval_label}' {'was' if passed else 'was NOT'} found during validation"
                    print(f"{tag} {msg}")
                    logger.log({"step": desc, "eval": tag, "labels": all_labels})
                    break

                else:
                    print(f"[EVAL][FAILED] Unknown step type: {typ}")
                    logger.log({"step": desc, "error": f"Unknown step type: {typ}"})
                    break
            except Exception as e:
                print(f"[EVAL][FAILED] Exception: {e}")
                logger.log({"step": desc, "error": str(e)})

        if not passed and step.get("on_fail"):
            of_cmd = step["on_fail"].get("command")
            if of_cmd:
                import subprocess
                check_command_safety(of_cmd)
                result = subprocess.run(of_cmd, shell=True, capture_output=True, text=True)
                print(f"[ON-FAIL] Output: {result.stdout.strip()}")
                logger.log({"step": desc, "on_fail_output": result.stdout.strip()})

        pipeline_eval_summary.append({
            "step": desc,
            "passed": passed,
            "required": required
        })

    min_passed = test_case.get("min_passed", None)
    total_required = sum(1 for pf in pipeline_eval_summary if pf.get("required", True))
    num_passed = sum(1 for pf in pipeline_eval_summary if pf.get("passed", False) and pf.get("required", True))

    if min_passed is not None:
        if num_passed >= min_passed:
            print(f"\n[PIPELINE][EVAL][PASSED] Minimum {min_passed} required steps passed ({num_passed}/{total_required}).")
            global_pass = True
        else:
            print(f"\n[PIPELINE][EVAL][FAILED] Only {num_passed} of {min_passed} required steps passed.")
            global_pass = False
    else:
        global_pass = (num_passed == total_required)
        if global_pass:
            print(f"\n[PIPELINE][EVAL][PASSED] All required steps passed ({num_passed}/{total_required}).")
        else:
            print(f"\n[PIPELINE][EVAL][FAILED] Not all required steps passed ({num_passed}/{total_required}).")

    logger.log({
        "event": "end_pipeline",
        "end_time": datetime.now().isoformat(),
        "global_pass": global_pass
    })
    logger.close()

    print("\n=== PIPELINE FINISHED ===")
    print(f"[PIPELINE] {'PASSED' if global_pass else 'FAILED'}")

    try:
        logfile = logger.log_file
        report_dir = logger.base_dir
        excel_path = os.path.join(report_dir, "report.xlsx")
        html_path = os.path.join(report_dir, "report.html")
        export_log_to_excel(logfile, excel_path)
        export_log_to_html(logfile, html_path)
        print(f"Reports generated: {excel_path} and {html_path}")
    except Exception as e:
        print(f"[WARNING] Report export failed: {e}")

if __name__ == "__main__":
    main()

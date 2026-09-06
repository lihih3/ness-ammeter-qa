import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, TypedDict


RESULTS_DIR = "results"


class TestResultRecord(TypedDict):
    run_id: str
    timestamp: str
    ammeter_type: str
    sampling_result: dict
    analysis_result: dict

# STEP 4
def save_test_result(ammeter_type: str, sampling_result: dict, analysis_result: dict) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    run_id = f"{timestamp}_{short_id}_{ammeter_type}"
    record: TestResultRecord = {
        "run_id": run_id,
        "timestamp": timestamp,
        "ammeter_type": ammeter_type,
        "sampling_result": sampling_result,
        "analysis_result": analysis_result,
    }

    file_path = os.path.join(RESULTS_DIR, f"{run_id}.json")
    with open(file_path, "w") as f:
        json.dump(record, f, indent=2)

    return run_id


def load_test_result(run_id: str) -> TestResultRecord:
    file_path = os.path.join(RESULTS_DIR, f"{run_id}.json")
    with open(file_path, "r") as f:
        return json.load(f)


def list_test_results() -> List[str]:
    if not os.path.isdir(RESULTS_DIR):
        return []

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".json")]
    return sorted(f[:-len(".json")] for f in files)

def load_analysis_results(run_ids: List[str]) -> Dict[str, dict]:
    """Load saved runs and return {label: analysis_result} - the input shape
    compare_ammeters() expects, so historical runs can be compared directly."""
    results: Dict[str, dict] = {}

    for run_id in run_ids:
        record = load_test_result(run_id)
        label = record["ammeter_type"]
        if label in results:  # same ammeter saved more than once
            label = f"{label}_{run_id}"
        results[label] = record["analysis_result"]

    return results
from typing import List, Optional, TypedDict
import statistics


class AnalysisResult(TypedDict):
    count: int
    total_count: int
    mean: Optional[float]
    median: Optional[float]
    stdev: Optional[float]
    min: Optional[float]
    max: Optional[float]
    error: Optional[str]
    note: Optional[str]

# STEP 3
def analyze_measurements(measurements: List[dict]) -> AnalysisResult:
    currents = [m["current"] for m in measurements if m.get("success")]

    result: AnalysisResult = {
        "count": len(currents),
        "total_count": len(measurements),
        "mean": None,
        "median": None,
        "stdev": None,
        "min": None,
        "max": None,
        "error": None,
        "note": None,
    }

    if not currents:
        result["error"] = "No successful measurements to analyze"
        return result

    result["mean"] = statistics.mean(currents)
    result["median"] = statistics.median(currents)
    result["min"] = min(currents)
    result["max"] = max(currents)

    if len(currents) >= 2:
        result["stdev"] = statistics.stdev(currents)
    else:
        result["note"] = "stdev requires at least 2 successful measurements"

    return result
from typing import Dict, Optional, TypedDict


class ComparisonResult(TypedDict):
    coefficient_of_variation: Dict[str, float]
    most_consistent: Optional[str]
    least_consistent: Optional[str]
    skipped: Dict[str, str]
    error: Optional[str]
    note: Optional[str]

# STEP 5
def compare_ammeters(analysis_results: Dict[str, dict]) -> ComparisonResult:
    cv_by_ammeter: Dict[str, float] = {}
    skipped: Dict[str, str] = {}

    for ammeter_type, analysis in analysis_results.items():
        mean = analysis.get("mean")
        stdev = analysis.get("stdev")

        if mean is None or stdev is None:
            skipped[ammeter_type] = "needs at least 2 successful measurements"
        elif mean == 0:
            skipped[ammeter_type] = "mean is zero, coefficient of variation is undefined"
        else:
            cv_by_ammeter[ammeter_type] = stdev / abs(mean)

    if not cv_by_ammeter:
        return {
            "coefficient_of_variation": {},
            "most_consistent": None,
            "least_consistent": None,
            "skipped": skipped,
            "error": "Not enough data to compare (need mean and stdev for at least one ammeter)",
            "note": None,
        }

    note = None
    if len(cv_by_ammeter) == 1:
        note = "only one ammeter had enough data - nothing to compare it against"

    return {
        "coefficient_of_variation": cv_by_ammeter,
        "most_consistent": min(cv_by_ammeter, key=cv_by_ammeter.get),
        "least_consistent": max(cv_by_ammeter, key=cv_by_ammeter.get),
        "skipped": skipped,
        "error": None,
        "note": note,
    }
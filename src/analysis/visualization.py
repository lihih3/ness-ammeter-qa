from typing import Dict, List, Optional
from datetime import datetime
import os
import matplotlib
matplotlib.use("Agg")  # no display needed, works on any OS
import matplotlib.pyplot as plt

from src.results import RESULTS_DIR
from src.utils.logger import TestLogger

logger = TestLogger("visualization")

DEFAULT_PLOT_TYPES = ["line"]


def plot_measurements(measurements: List[dict], ammeter_type: str,
                      output_dir: str = RESULTS_DIR,
                      plot_types: Optional[List[str]] = None) -> Dict[str, str]:
    """Draw one chart per requested plot type. Returns {plot_type: file_path}."""
    currents = [m["current"] for m in measurements if m.get("success")]

    if not currents:
        logger.warning(f"{ammeter_type}: no successful measurements to plot")
        return {}

    if not plot_types:
        plot_types = DEFAULT_PLOT_TYPES

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created: Dict[str, str] = {}

    for plot_type in plot_types:
        plt.figure()

        if plot_type == "line":
            # How the current changes from sample to sample.
            plt.plot(range(1, len(currents) + 1), currents, marker="o")
            plt.xlabel("Sample number")
            plt.ylabel("Current (A)")
            plt.title(f"{ammeter_type} - measured current per sample")

        elif plot_type == "histogram":
            # How the measurements are distributed - the spread that the
            # coefficient of variation (Step 5) measures numerically.
            plt.hist(currents, bins="auto", edgecolor="black")
            plt.xlabel("Current (A)")
            plt.ylabel("Number of samples")
            plt.title(f"{ammeter_type} - distribution of measured current")

        else:
            plt.close()
            logger.warning(f"{ammeter_type}: unknown plot type '{plot_type}', skipped")
            continue

        file_path = os.path.join(output_dir, f"{ammeter_type}_{plot_type}_{timestamp}.png")
        plt.savefig(file_path)
        plt.close()

        created[plot_type] = file_path
        logger.info(f"{ammeter_type}: {plot_type} chart saved to {file_path}")

    return created
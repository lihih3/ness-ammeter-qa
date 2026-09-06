import socket
import threading
import time

from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Circutor_Ammeter import CircutorAmmeter
from src.testing.test_framework import AmmeterTestFramework
from src.analysis.stats import analyze_measurements
from src.analysis.visualization import plot_measurements
from src.analysis.comparison import compare_ammeters
from src.results import save_test_result, load_test_result, list_test_results, load_analysis_results

AMMETER_TYPES = ["greenlee", "entes", "circutor"]


class FaultyAmmeterServer:
    """A deliberately broken ammeter server, used to simulate error conditions on demand."""

    def __init__(self, port: int, fault: str):
        self.port = port
        self.fault = fault  # "bad_data", "no_response" or "hang"

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("localhost", self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    conn.recv(1024)
                    if self.fault == "bad_data":
                        conn.sendall(b"NOT_A_NUMBER")
                    elif self.fault == "hang":
                        time.sleep(30)  # accepts the connection but never answers
                    # "no_response": close without sending anything


def start_servers():
    threading.Thread(target=lambda: GreenleeAmmeter(5001).start_server(), daemon=True).start()
    threading.Thread(target=lambda: EntesAmmeter(5002).start_server(), daemon=True).start()
    threading.Thread(target=lambda: CircutorAmmeter(5003).start_server(), daemon=True).start()
    time.sleep(2)


def section1_demo(framework):
    print("\n=== Section 1: run_test ===")

    for ammeter_type in AMMETER_TYPES:
        result = framework.run_test(ammeter_type)
        print(f"[expected] {ammeter_type}: {result}")

    result = framework.run_test("unknown_ammeter")
    print(f"[unexpected - unknown type] {result}")


def section2_demo(framework):
    print("\n=== Section 2: run_sampling_test ===")

    sampling_results = {}
    for ammeter_type in AMMETER_TYPES:
        result = framework.run_sampling_test(ammeter_type)
        sampling_results[ammeter_type] = result
        print(f"[expected] {ammeter_type}: "
              f"{result['actual_count']}/{result['requested_count']} measurements, "
              f"{result['actual_duration_seconds']:.2f}s")

    unknown_result = framework.run_sampling_test("unknown_ammeter")
    all_failed = all(not m["success"] for m in unknown_result["measurements"])
    print(f"[unexpected - unknown type] {unknown_result['actual_count']} measurements, all failed: {all_failed}")

    return sampling_results, unknown_result


def section3_demo(framework, sampling_results, unknown_result):
    print("\n=== Section 3: analyze_measurements + visualization ===")

    config = framework.config.get("analysis", {}).get("visualization", {})
    plots_enabled = config.get("enabled", True)
    if not plots_enabled:
        print("[config] analysis.visualization.enabled is false - charts skipped")

    plot_types = config.get("plot_types")
    analysis_results = {}
    for ammeter_type in AMMETER_TYPES:
        measurements = sampling_results[ammeter_type]["measurements"]

        stats = analyze_measurements(measurements)
        analysis_results[ammeter_type] = stats
        print(f"[expected] {ammeter_type} stats: {stats}")

        if plots_enabled:
            charts = plot_measurements(measurements, ammeter_type, plot_types=plot_types)
            print(f"[expected] {ammeter_type} charts: {charts}")

    unknown_stats = analyze_measurements(unknown_result["measurements"])
    print(f"[unexpected - no successful measurements] stats: {unknown_stats}")

    if plots_enabled:
        charts = plot_measurements(unknown_result["measurements"], "unknown_ammeter", plot_types=plot_types)
        print(f"[unexpected - no successful measurements] charts: {charts}")

    return analysis_results, unknown_stats


def section4_demo(sampling_results, analysis_results):
    print("\n=== Section 4: result archiving ===")

    run_ids = {}
    for ammeter_type in AMMETER_TYPES:
        run_id = save_test_result(ammeter_type, sampling_results[ammeter_type], analysis_results[ammeter_type])
        run_ids[ammeter_type] = run_id
        print(f"[expected] saved {ammeter_type}: {run_id}")

    print(f"[expected] all saved runs: {list_test_results()}")

    for ammeter_type in AMMETER_TYPES:
        loaded = load_test_result(run_ids[ammeter_type])
        print(f"[expected] loaded {ammeter_type}: {loaded['run_id']}")

    try:
        load_test_result("does_not_exist")
    except FileNotFoundError as e:
        print(f"[unexpected - bad run_id, raises by design] {e}")

    return run_ids


def section5_demo(analysis_results, unknown_stats, run_ids):
    print("\n=== Section 5: compare_ammeters (bonus) ===")

    comparison = compare_ammeters(analysis_results)
    print(f"[expected] {comparison}")

    comparison = compare_ammeters({"unknown_ammeter": unknown_stats})
    print(f"[unexpected - no valid data to compare] {comparison}")

    comparison = compare_ammeters({**analysis_results, "unknown_ammeter": unknown_stats})
    print(f"[unexpected - one ammeter unusable, the rest still compared] {comparison}")

    historical = load_analysis_results(list(run_ids.values()))
    print(f"[expected - compared from saved files] {compare_ammeters(historical)}")


def error_simulation_demo(framework):
    print("\n=== Bonus: Error Simulation ===")

    threading.Thread(target=FaultyAmmeterServer(5098, "bad_data").start, daemon=True).start()
    threading.Thread(target=FaultyAmmeterServer(5097, "no_response").start, daemon=True).start()
    threading.Thread(target=FaultyAmmeterServer(5095, "hang").start, daemon=True).start()
    time.sleep(1)

    framework.config["ammeters"]["faulty_data"] = {"port": 5098, "command": "ANY"}
    framework.config["ammeters"]["faulty_no_response"] = {"port": 5097, "command": "ANY"}
    framework.config["ammeters"]["faulty_offline"] = {"port": 5096, "command": "ANY"}  # nothing listens here
    framework.config["ammeters"]["faulty_hang"] = {"port": 5095, "command": "ANY"}

    result = framework.run_test("faulty_data")
    print(f"[simulated - corrupted data] {result}")

    result = framework.run_test("faulty_no_response")
    print(f"[simulated - no response] {result}")

    result = framework.run_test("faulty_offline")
    print(f"[simulated - server offline] {result}")

    result = framework.run_test("faulty_hang")
    print(f"[simulated - server hangs, no answer] {result}")


def main():
    start_servers()
    framework = AmmeterTestFramework()

    section1_demo(framework)
    sampling_results, unknown_result = section2_demo(framework)
    analysis_results, unknown_stats = section3_demo(framework, sampling_results, unknown_result)
    run_ids = section4_demo(sampling_results, analysis_results)
    section5_demo(analysis_results, unknown_stats, run_ids)
    error_simulation_demo(framework)


if __name__ == "__main__":
    main()
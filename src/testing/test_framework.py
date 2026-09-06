from typing import Dict, List
import socket
import time
from ..utils.config import load_config
from ..utils.logger import TestLogger


class AmmeterTestFramework:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_config(config_path)
        self.logger = TestLogger("ammeter_test_framework")

    # STEP 1
    def run_test(self, ammeter_type: str) -> Dict:
        ammeters = self.config.get("ammeters", {})

        if ammeter_type not in ammeters:
            self.logger.error(f"{ammeter_type}: unknown ammeter type")
            return {
                "ammeter_type": ammeter_type,
                "port": None,
                "success": False,
                "current": None,
                "error": f"Unknown ammeter type: '{ammeter_type}'",
            }

        port = ammeters[ammeter_type]["port"]
        command = ammeters[ammeter_type]["command"].encode()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect(("localhost", port))
                s.sendall(command)
                data = s.recv(1024)
            if not data:
                self.logger.error(f"{ammeter_type}: no data received")
                return {
                    "ammeter_type": ammeter_type,
                    "port": port,
                    "success": False,
                    "current": None,
                    "error": "No data received from ammeter (command may not match)",
                }

            current = float(data.decode("utf-8"))
            self.logger.info(f"{ammeter_type}: success, current={current}")
            return {
                "ammeter_type": ammeter_type,
                "port": port,
                "success": True,
                "current": current,
                "error": None,
            }


        except (OSError, ValueError) as e:
            self.logger.error(f"{ammeter_type}: {e}")
            return {
                "ammeter_type": ammeter_type,
                "port": port,
                "success": False,
                "current": None,
                "error": str(e),
            }

    # STEP 2
    def run_sampling_test(self, ammeter_type: str) -> Dict:
        sampling = self.config.get("testing", {}).get("sampling", {})
        count = sampling["measurements_count"]
        frequency = sampling["sampling_frequency_hz"]
        max_duration = sampling["total_duration_seconds"]
        interval = 1 / frequency

        measurements: List[Dict] = []
        start = time.monotonic()
        deadline = start + max_duration

        for i in range(count):
            next_tick = start + i * interval
            now = time.monotonic()
            if next_tick > now:
                time.sleep(next_tick - now)

            if time.monotonic() >= deadline:
                break

            measurements.append(self.run_test(ammeter_type))

        actual_duration = time.monotonic() - start

        return {
            "ammeter_type": ammeter_type,
            "measurements": measurements,
            "requested_count": count,
            "actual_count": len(measurements),
            "requested_duration_seconds": max_duration,
            "actual_duration_seconds": actual_duration,
        }
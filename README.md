# Ammeter Testing Framework

A testing framework for current-measurement ammeter emulators - Greenlee,
ENTES and CIRCUTOR. Each emulator runs on its own thread and answers
measurement requests over a socket; the framework queries them through one
unified API, samples them over time, analyses the results, archives every
run and compares the ammeters against each other.

## Project Structure

- `main.py`: Starts the three emulators and requests one measurement from each.
- `Ammeters/`
  - `Circutor_Ammeter.py`: Emulator for the CIRCUTOR ammeter.
  - `Entes_Ammeter.py`: Emulator for the ENTES ammeter.
  - `Greenlee_Ammeter.py`: Emulator for the Greenlee ammeter.
  - `base_ammeter.py`: Base class for all ammeter emulators.
  - `client.py`: Client to request current measurements from the emulators.
- `config/`
  - `config.yaml`: Ports, commands, sampling settings and chart options.
- `src/`
  - `testing/`
    - `test_framework.py`: `AmmeterTestFramework` - one measurement (`run_test`)
      or a full sampling run (`run_sampling_test`).
  - `analysis/`
    - `stats.py`: Mean, median, standard deviation, min and max.
    - `comparison.py`: Compares ammeters and identifies the most consistent.
    - `visualization.py`: Saves line and histogram charts as PNG files.
  - `results.py`: Stores each test run as a JSON file with a unique ID, so past
    runs can be found, reloaded and compared later.
  - `utils/`
    - `config.py`: Loads `config.yaml`.
    - `logger.py`: `TestLogger` - one log file per run, shared by all components.
    - `Utils.py`: Utility functions, including `generate_random_float`.
- `examples/`
  - `run_tests.py`: Full working demo of every feature, including error cases.
- `results/`: Generated output, not tracked in git (see `.gitignore`):
  - JSON files: saved test runs.
  - PNG files: measurement charts.
  - `logs/`: log file per run.
  - `samples/`: a committed example of all three, for reference.
- `DESIGN_DECISIONS.md`: Design choices, bugs found and fixed, and verification.

## Setup

Requires Python 3.9 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Only two packages are needed: `pyyaml` for the config file and `matplotlib`
for the charts. Everything else uses the Python standard library.

## Usage

**Run the full test suite** - this is the main entry point:

```sh
python -m examples.run_tests
```

It starts all three emulators and walks through every feature in order:
single measurements, sampling over time, statistical analysis, charts,
result archiving, ammeter comparison, and four simulated failures. Each line
is labelled `[expected]` or `[unexpected]` so you can see which cases are
normal results and which are error handling.

Note the `-m` - the demo must be run as a module from the project root, so
that `src/` and `Ammeters/` resolve correctly.

**Run the basic emulator demo** (starts the emulators and requests one
measurement from each):

```sh
python main.py
```

Run one or the other, not both at once - they use the same ports.

## Configuration

All behaviour is set in `config/config.yaml`; no code changes needed.

```yaml
testing:
  sampling:
    measurements_count: 10        # how many measurements to take
    total_duration_seconds: 5     # hard time budget for the run
    sampling_frequency_hz: 2      # how often to measure

ammeters:                         # port and command for each ammeter
  greenlee:
    port: 5001
    command: "MEASURE_GREENLEE -get_measurement"
  ...

analysis:
  visualization:
    enabled: true                 # set false to skip charts entirely
    plot_types: ["line", "histogram"]
```

Adding a fourth ammeter needs only a new entry under `ammeters` - the
framework reads its port and command from here.

## Output

Each run writes to `results/`:

| File | Contents |
|------|----------|
| `*.json` | One per test run - measurements, timings and statistics, under a unique run ID |
| `*_line_*.png` | Current per sample number |
| `*_histogram_*.png` | Distribution of the measured currents |
| `logs/*_test_run.log` | Every measurement and every failure, with timestamps |

Filenames carry the ammeter name and a timestamp, so a file can be
identified without opening it. `results/samples/` holds one committed
example of each.

## Ammeter Reference

### Greenlee Ammeter
- **Port**: 5001
- **Command**: `MEASURE_GREENLEE -get_measurement`
- **Measurement logic**: Voltage (1V - 10V) and resistance (0.1Ω - 100Ω)
- **Method**: Ohm's Law, I = V / R

### ENTES Ammeter
- **Port**: 5002
- **Command**: `MEASURE_ENTES -get_data`
- **Measurement logic**: Magnetic field (0.01T - 0.1T) and calibration factor (500 - 2000)
- **Method**: Hall Effect, I = B * K

### CIRCUTOR Ammeter
- **Port**: 5003
- **Command**: `MEASURE_CIRCUTOR -get_measurement -current`
- **Measurement logic**: Voltage samples (0.1V - 1.0V) over a random time step (0.001s - 0.01s)
- **Method**: Rogowski Coil Integration, I = ∫V dt

## Troubleshooting

**"Address already in use"** - another copy of the emulators is still
running. Close the other process, or wait a moment and retry.

**`ModuleNotFoundError: No module named 'Ammeters'`** - the demo was run as a
script instead of a module. Use `python -m examples.run_tests` from the
project root.

**`ModuleNotFoundError: No module named 'yaml'`** - the virtual environment
isn't active. Run `source .venv/bin/activate` first.

## Design Decisions

See `DESIGN_DECISIONS.md` for the design choices behind each part, the four
bugs found in the provided code and how they were fixed, and the verification
output for every feature.
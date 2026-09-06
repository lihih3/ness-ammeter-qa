# Design Decisions

Design documentation for the Ness Technologies ammeter testing exercise.
Every feature and every error case described here is demonstrated by one
runnable script:

```sh
python -m examples.run_tests
```

---

## Summary

A testing framework for three ammeter emulators (Greenlee, ENTES, CIRCUTOR)
covering all five problem areas plus all four bonus challenges.

**Four bugs were found in the given code and fixed:**

| # | Where | Problem |
|---|-------|---------|
| 1 | `main.py` | Requests disabled, and the commands didn't match what the servers expect |
| 2 | `config/config.yaml` | CIRCUTOR command missing its `-current` suffix |
| 3 | `src/utils/logger.py` | `TestLogger` never attached a file handler - nothing was ever logged |
| 4 | `Ammeters/base_ammeter.py` | Sockets couldn't rebind after a run, silently corrupting test results |

**Principles applied throughout:**

- One consistent result shape for every outcome, success or failure.
- Nothing fails silently - every skipped or failed item is reported with a reason.
- Behaviour comes from `config/config.yaml`, not hardcoded values.
- The framework never hangs: every wait has a deadline.

## Libraries installed

```
pyyaml>=6.0        # loading config/config.yaml
matplotlib>=3.4.0  # charts (visualization bonus)
```

Everything else uses the standard library - `socket`, `threading`,
`statistics`, `json`, `uuid`, `logging`, `datetime`.

The file originally also listed numpy, scipy, seaborn and pandas. None are
imported anywhere, so they were removed: the spec asks to minimize external
dependencies, and installing ~200MB of unused packages works against that.

---

## Bugs found in the given code

### Bug 1 - `main.py` returned no data

The ammeter requests were commented out, and once enabled the commands
didn't exactly match what each server expects. `base_ammeter.py` compares
received bytes against `get_current_command` with `==`, so anything not an
exact match gets no reply at all.

**Fixed** by correcting the three commands. `python main.py` after the fix:

```
Received current measurement from port 5001: 0.0527909033405795 A
Received current measurement from port 5002: 42.38490096803135 A
Received current measurement from port 5003: 0.03029496747616526 A
```

### Bug 2 - CIRCUTOR command wrong in `config.yaml`

The same mismatch in the config file - the `circutor` entry was missing
`-current`, so every CIRCUTOR measurement through the framework silently
returned nothing. **Fixed.**

### Bug 3 - `TestLogger` never wrote to disk

`_setup_logger` built a log file path and created the logs directory, but
never attached a `FileHandler` and never called `setLevel`. Python's default
level is WARNING and a logger with no handler discards its output, so every
`.info()` call was thrown away - while the created directory made it look
like logging worked.

**Fixed** by setting the level and attaching a handler. Logging calls were
then added to `run_test`, one line per success and per error.

**What is not logged:** the emulators and `client.py` keep their `print`
statements. They simulate hardware - their output is the device's own
console, not the framework's record - and mixing it into the log would blur
the line between the system under test and the system doing the testing.
The demo script prints for the same reason: its job is showing results to a
person. Logging is for the framework's own internal record.

### Bug 4 - emulator sockets could not rebind between runs

`base_ammeter.py` binds without `SO_REUSEADDR`, so a port still in
`TIME_WAIT` from a previous run rejects the next one with "Address already
in use". The given code acknowledges the symptom but not the cause -
`main.py` shipped with the comment *"if you have problem restarting the
servers between runs try increasing sleep time"*. Waiting longer only hides
it.

This mattered more than a slow start-up: when the bind fails, the server
thread dies while the test run carries on. The error simulation then
reported "Connection refused" for cases that should have shown a parsing
error or "No data received" - the tests still passed, but were testing
something other than what they claimed. Silently wrong results are the worst
failure mode a QA tool can have.

**Fixed** by setting `SO_REUSEADDR` before `bind()` in `base_ammeter.py` and
in the demo's `FaultyAmmeterServer`.

**Verification:** before the fix, two runs in a row failed the second time
with `[Errno 98] Address already in use` and three dead server threads.
After, three consecutive runs with no wait between them are clean.

---

## 1. Unified Measurement API

`AmmeterTestFramework.run_test(ammeter_type)`

Queries any of the three ammeters through one function and always returns
the same five keys: `ammeter_type`, `port`, `success`, `current`, `error`.

**Consistent reporting:** the shape is identical whether the measurement
worked or failed, so callers never need to know which case they're handling.
`run_sampling_test`, `analyze_measurements` and the demo all rely on this.

**Configuration-driven:** each ammeter's port and command live in
`config.yaml`. The framework knows nothing ammeter-specific - it looks up
the config and connects, so adding a fourth ammeter needs no code change.

**Four failure cases** are handled, all returning `success: False` with a
clear message: unknown ammeter type, connection failure, a server that
accepts but never answers, and non-numeric data (`ValueError` from
`float()`).

**Socket timeout:** the client sets `settimeout(5)`. Without it, an ammeter
that accepts a connection but never replies blocks `recv()` forever and
freezes the whole run. For a test framework a hang is worse than a failure:
it reports nothing *and* blocks everything after it. `TimeoutError` is a
subclass of `OSError`, so the existing handler catches it and reports it
like any other failure. `ConnectionRefusedError` was removed from that
`except` clause for the same reason - also an `OSError` subclass, so listing
it was redundant.

**One log file per run:** `TestLogger` originally created a file per logger
name, so a run produced one file for the framework and another for
visualization - you had to merge timestamps by hand to see that a chart was
skipped *because* the measurements failed a moment earlier. Standard Python
practice is many named loggers writing to one destination, so the handler is
configured once on a parent logger (`ammeter_qa`) with each component as a
child. The component name appears in every line, so nothing is lost by
merging. The parent is named rather than root - attaching to root would also
capture matplotlib's debug output and flood the file.

**Verification:**

```
{'ammeter_type': 'greenlee', 'port': 5001, 'success': True, 'current': 0.12796134056745817, 'error': None}
{'ammeter_type': 'entes', 'port': 5002, 'success': True, 'current': 163.80732779694262, 'error': None}
{'ammeter_type': 'circutor', 'port': 5003, 'success': True, 'current': 0.04057749661907015, 'error': None}

# Unknown type / offline / never answers / corrupted data:
{'ammeter_type': 'unknown_ammeter', 'port': None, 'success': False, 'error': "Unknown ammeter type: 'unknown_ammeter'"}
{'ammeter_type': 'faulty_offline', 'port': 5096, 'success': False, 'error': '[Errno 61] Connection refused'}
{'ammeter_type': 'faulty_hang', 'port': 5095, 'success': False, 'error': 'timed out'}
{'ammeter_type': 'faulty_data', 'port': 5098, 'success': False, 'error': "could not convert string to float: 'NOT_A_NUMBER'"}
```

## 2. Measurement Sampling

`AmmeterTestFramework.run_sampling_test(ammeter_type)`

Takes repeated measurements at a configurable count, frequency and total
duration, and returns them with timing information.

**Precise timing:** uses `time.monotonic()` with absolute scheduled
timestamps (`start + i * interval`) rather than sleeping between
measurements. With naive sleeping, the time each measurement takes is added
to every interval and the error accumulates. Scheduling against fixed points
keeps samples on time however long any measurement takes.

**What each config value controls:** the three sampling values are
over-determined - any two determine the third (10 samples at 2 Hz *is* 4.5
seconds). Rather than let one silently contradict the others, each has a
distinct job:

| Setting | Controls |
|---|---|
| `sampling_frequency_hz` | how often to measure |
| `measurements_count` | how many to target |
| `total_duration_seconds` | a hard time budget for the run |

Frequency and count define the schedule; duration is an independent upper
bound. If the run hits the deadline first it stops and reports the truth:
`actual_count: 10` out of `requested_count: 20`.

**Why the budget matters:** because of the 5-second timeout from Section 1.
A broken ammeter makes every measurement take 5 seconds instead of
milliseconds, so a "10 samples in 5 seconds" run would quietly take 50. The
budget stops it on time, and the low `actual_count` shows something is wrong.

**Note on duration:** in a healthy run `actual_duration_seconds` lands
slightly below the requested value (~4.5s vs 5s). Expected: the first sample
starts at t=0, so N samples span `(N-1)/frequency` seconds. Both values are
returned, so the difference is visible rather than hidden.

**Verification:**

```
# Normal - count 10, 2 Hz, budget 5s:
greenlee: 10/10 measurements, 4.50s
entes:    10/10 measurements, 4.51s
circutor: 10/10 measurements, 4.50s
(near-identical duration across three very different implementations,
 confirming no timing drift)

# count raised to 20, budget still 5s - the budget caps it:
greenlee: 10/20 measurements, 5.00s
entes:    10/20 measurements, 5.00s
circutor: 10/20 measurements, 5.00s
```

## 3. Result Analysis

`analyze_measurements(measurements)` - `src/analysis/stats.py`

Computes mean, median, standard deviation, min and max of the current
values. Only successful measurements are included.

**Design decisions:**

- Lives in its own module, separate from `AmmeterTestFramework`. It only
  processes data - it knows nothing about sockets or ammeters. This keeps
  "how we get the data" apart from "what we do with it", and means it can be
  tested with a plain list of dicts, no servers required.
- Uses the built-in `statistics` module rather than numpy, per the
  minimize-dependencies constraint.
- Return shape defined with `TypedDict`, so every field is typed.
- A plain function, not a class: there is no state to carry between calls.
  `AmmeterTestFramework` is a class because it holds `config` and a logger;
  this holds nothing. Same reasoning for `compare_ammeters`.
- Returns both `count` (successful) and `total_count` (attempted). Without
  `total_count`, a result of `count: 7` gives no hint that 3 measurements
  failed - the statistics would look healthy while a third of the data was
  missing.

**Edge cases:** no successful measurements sets `error` and leaves all
statistics `None`; exactly one sets `stdev` to `None` with a `note`, since
standard deviation needs at least two points.

**Observation:** circutor is usually the most stable and greenlee always the
least. This follows from their formulas - circutor sums ten random voltage
samples, and combining independent draws reduces relative variability, while
greenlee computes `V / R` from a single pair and, because `R` can approach
0.1Ω, is heavy-tailed. Section 5 quantifies this.

**Verification** (10/10 successful each):

```
greenlee: {'count': 10, 'total_count': 10, 'mean': 0.121, 'median': 0.095, 'stdev': 0.084, 'min': 0.049, 'max': 0.326}
entes:    {'count': 10, 'total_count': 10, 'mean': 76.32, 'median': 64.18, 'stdev': 42.51, 'min': 30.70, 'max': 141.07}
circutor: {'count': 10, 'total_count': 10, 'mean': 0.037, 'median': 0.037, 'stdev': 0.016, 'min': 0.013, 'max': 0.066}

# All measurements failed:
{'count': 0, 'total_count': 10, 'mean': None, ..., 'error': 'No successful measurements to analyze'}
```

### 3a. Bonus - Visualization

`plot_measurements(...)` - `src/analysis/visualization.py`

Draws one chart per requested plot type, saves each as a PNG in `results/`,
and returns `{plot_type: file_path}` - or `{}` if there was nothing to plot.

**Design decisions:**

- Two chart types, chosen from `config.yaml` via
  `analysis.visualization.plot_types`: a **line** chart showing how current
  moves sample to sample, and a **histogram** showing the distribution. The
  histogram is the visual counterpart to Section 5 - the coefficient of
  variation states the spread as a number, the histogram shows its shape.
  greenlee's is visibly right-skewed, most samples low with a couple of
  large outliers, which is exactly why its CV is the worst of the three.
- `analysis.visualization.enabled` is honoured, so charts can be switched
  off from config without touching code.
- An unrecognised plot type logs a warning and is skipped; valid ones are
  still drawn. A typo in a config file shouldn't abort a test run.
- Uses matplotlib's `Agg` backend and writes to a file rather than opening a
  window - any OS, no display needed, safe headless.
- Filenames include type and timestamp
  (`greenlee_histogram_20260906_140054.png`), so each run's charts are kept,
  matching how Section 4 archives runs under unique IDs.
- `output_dir` is a parameter defaulting to `RESULTS_DIR`, so the caller can
  redirect output instead of it being hardcoded.
- On "nothing to plot" it logs a warning and returns `{}` rather than
  printing. A library function shouldn't print - the caller decides what to
  show, and the event is still in the log.

**Verification:** six charts generated (line + histogram per ammeter) and
visually checked. Each matches the statistics above - circutor's line chart
is flattest, greenlee's histogram shows the outliers behind its variability.

```
[INFO]    ammeter_qa.visualization: greenlee: line chart saved to results/greenlee_line_20260906_140054.png
[INFO]    ammeter_qa.visualization: greenlee: histogram chart saved to results/greenlee_histogram_20260906_140054.png
[WARNING] ammeter_qa.visualization: unknown_ammeter: no successful measurements to plot
```

## 4. Result Management

`src/results.py`

Saves each test run as a JSON file with a unique run ID, and lists, loads
and compares saved runs afterwards.

**Design decisions:**

- Run ID = timestamp + short `uuid` suffix + ammeter name, e.g.
  `20260906_140055_31168131_greenlee`. The timestamp comes first so IDs sort
  chronologically when sorted alphabetically - which `list_test_results()`
  relies on; the random suffix keeps them unique for runs saved in the same
  second; the ammeter name means a saved file can be identified without
  opening it, matching how the charts are named.
- Stored as JSON: standard library, no extra dependency, readable without
  special tools.
- `load_test_result` raises on an unknown run ID. That's a caller bug, not
  an external failure like a network error, so it isn't swallowed into a
  `success: False` result.
- `load_analysis_results(run_ids)` loads saved runs and returns them in
  exactly the shape `compare_ammeters` expects. The spec asks for "easy
  retrieval **and comparison** of historical results" - retrieval alone
  wasn't enough. Without it, comparing runs from an earlier execution meant
  opening each file and reading numbers by hand. It also disambiguates
  labels, so comparing two runs of the same ammeter doesn't overwrite one.

**What is committed:** `results/` is excluded from git as generated output.
A small `results/samples/` folder is committed as the "sample test results"
deliverable, so the repository holds real examples without accumulating
every run.

**Verification:** saved three runs, listed them, loaded each back, then
compared them straight from the saved files. The comparison rebuilt from
disk is identical to the one computed in memory during the same run,
confirming the JSON round-trip loses nothing. Running the demo again adds
three more and `list_test_results()` returns all of them, confirming the
archive persists across executions.

```
[expected] all saved runs: ['20260906_140055_31168131_greenlee', '20260906_140055_54ff572b_circutor', '20260906_140055_b921e339_entes']

# Bad run ID - raises by design:
[Errno 2] No such file or directory: 'results/does_not_exist.json'

# In memory vs. rebuilt from the saved files - identical:
{'greenlee': 1.2564, 'entes': 0.6030, 'circutor': 0.4415}
{'greenlee': 1.2564, 'entes': 0.6030, 'circutor': 0.4415}
```

## 5. Accuracy Assessment - Bonus

`compare_ammeters(analysis_results)` - `src/analysis/comparison.py`

Compares ammeters by coefficient of variation (stdev / mean) and names the
most and least consistent.

**Precision, not accuracy:** true accuracy needs a known reference current
to compare against, and none exists in this simulated setup. So this
measures relative **precision** - how tightly readings cluster - as the best
available proxy for reliability. Stated explicitly rather than labelled
"accuracy", because claiming more than the data supports would mislead.

**Coefficient of variation, not standard deviation:** the three ammeters
read on completely different scales (entes in tens of amps, circutor in
hundredths). Raw standard deviation would rank them by magnitude. Dividing
by the mean makes the spread comparable across scales.

**Nothing is dropped silently:** an ammeter that can't be compared (fewer
than two successful measurements, or a mean of zero) is listed in `skipped`
with the reason instead of vanishing - the same principle as `total_count`
in Section 3. A `note` is returned when only one ammeter had usable data,
since `most_consistent` and `least_consistent` would then both name it,
which looks like a comparison but isn't one.

**Verification:**

```
# All three:
{'coefficient_of_variation': {'greenlee': 1.598, 'entes': 0.424, 'circutor': 0.503},
 'most_consistent': 'entes', 'least_consistent': 'greenlee',
 'skipped': {}, 'error': None, 'note': None}

# One unusable - the rest still compared, and it is reported:
{'coefficient_of_variation': {'greenlee': 1.598, 'entes': 0.424, 'circutor': 0.503},
 'most_consistent': 'entes', 'least_consistent': 'greenlee',
 'skipped': {'unknown_ammeter': 'needs at least 2 successful measurements'}}

# Nothing usable at all:
{'coefficient_of_variation': {}, 'most_consistent': None, 'least_consistent': None,
 'skipped': {'unknown_ammeter': 'needs at least 2 successful measurements'},
 'error': 'Not enough data to compare (need mean and stdev for at least one ammeter)'}
```

## Bonus - Error Simulation

A small on-demand faulty server (in `examples/run_tests.py` only - the given
emulators are untouched) reproduces four real-world failures on demand, so
the error handling can be demonstrated rather than described.

**Why fault injection:** a framework's error handling is the part least
likely to be exercised by normal use, so it needs to be triggerable
deliberately. Each fault runs on its own port and is registered in the
framework's config like any other ammeter, so it goes through exactly the
same `run_test` code path as a real one - no special-casing.

**Verification:** all four handled without crashing.

```
corrupted data       -> "could not convert string to float: 'NOT_A_NUMBER'"
no response          -> "No data received from ammeter (command may not match)"
server offline       -> "[Errno 61] Connection refused"
server never answers -> "timed out"   (after 5s - proves the socket timeout)
```

## Bonus - Configuration-driven testing

Everything that could reasonably change lives in `config/config.yaml`:
ammeter ports and commands, sampling count, frequency and duration, and
whether charts are drawn and which types.

**Unused keys removed:** the given config contained empty placeholders -
`analysis.statistical_metrics`, `analysis.visualization.plot_types` and
`result_management`. `plot_types` was implemented (see 3a). The other two
were removed rather than left blank: all five statistical metrics are
required by the spec, so making them switchable would contradict it, and
honouring `result_management` would mean giving `src/results.py` a config
dependency it doesn't otherwise need. The config now contains exactly what
the code reads, so a leftover placeholder can't be mistaken for an
unfinished feature.

## Known limitations

**Ten samples is not enough to identify the most precise ammeter.** Repeated
runs sometimes name circutor most consistent and sometimes entes. Simulating
the three formulas directly (100,000 samples each) gives their true
coefficients of variation:

| Ammeter | True CV | Wins "most consistent" at 10 samples |
|---|---|---|
| greenlee | 4.85 | 3% |
| entes | 0.61 | 27% |
| circutor | 0.50 | 70% |

So circutor really is the most precise, but at ten samples the framework
only says so 70% of the time - and greenlee, ten times worse than either,
still wins occasionally by luck. greenlee also shows why: its measured CV in
a ten-sample run (0.7-1.6) badly underestimates its true 4.85, because
`I = V / R` with `R` reaching 0.1Ω is heavy-tailed and the occasional very
large current usually doesn't appear in ten draws.

**In practice:** the framework reliably identifies the *worst* ammeter, but
separating the best two needs more samples than the current 5-second budget
allows. Raising `measurements_count` and `total_duration_seconds` together
would resolve it. This is documented rather than hidden, because a framework
that reports an unstable verdict as fact is worse than one that states its
own confidence.
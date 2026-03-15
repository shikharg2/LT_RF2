# LoadTest Framework - Technical Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Component Details](#component-details)
4. [Docker Infrastructure](#docker-infrastructure)
5. [Database Design](#database-design)
6. [Execution Pipeline](#execution-pipeline)
7. [Test Module Internals](#test-module-internals)
8. [Scheduler & Worker System](#scheduler--worker-system)
9. [Metric Collection & Evaluation](#metric-collection--evaluation)
10. [Unit Conversion System](#unit-conversion-system)
11. [Error Handling](#error-handling)
12. [Configuration Validation](#configuration-validation)
13. [Packaging & Distribution](#packaging--distribution)
14. [Extending the Framework](#extending-the-framework)

---

## Architecture Overview

The LoadTest Framework follows a distributed architecture built on Docker Swarm:

- **Orchestrator** (`orchestrate.py`) - Host-side process that manages the test lifecycle
- **Workers** (`src/worker.py`) - Run inside Docker containers, one per scenario
- **Scheduler** (`src/scheduler.py`) - APScheduler-based job scheduling inside each worker
- **Test Modules** (`src/test_modules/`) - Protocol-specific test implementations
- **PostgreSQL** - Centralized metrics database running as a Docker container
- **GUI** (`gui.py`) - PyQt5 desktop interface for configuration and monitoring

### Key Design Decisions

- **One worker per scenario** - Each scenario gets its own Docker Swarm service with one replica. This provides isolation and clean resource accounting.
- **Workers handle scheduling** - The orchestrator deploys workers and monitors them; scheduling logic (once/recurring) is handled inside each worker via APScheduler.
- **Database as central store** - All workers write metrics to a shared PostgreSQL instance over the Docker overlay network. The orchestrator reads from the same database for periodic CSV export.
- **Swarm overlay network** - All containers communicate via the `loadtest-network` overlay network, which allows service discovery by container name.

---

## Project Structure

```
LT_RF/
├── gui.py                     # PyQt5 GUI application
├── orchestrate.py             # Main orchestrator (CLI entry point)
├── cleanup.py                 # Docker resource cleanup script
├── setup.sh                   # First-time setup script
├── install_sipp.sh            # SIPp build-from-source script
├── Dockerfile                 # Worker container image definition
├── requirements.txt           # Python dependencies
├── build_deb.sh               # Debian package build script
├── configurations/
│   └── main.json              # Default configuration file
├── src/
│   ├── __init__.py
│   ├── scheduler.py           # APScheduler-based scenario scheduler
│   ├── worker.py              # Docker container worker entry point
│   ├── test_modules/
│   │   ├── __init__.py
│   │   ├── speed_test.py      # iperf3 bandwidth testing
│   │   ├── web_browsing.py    # Playwright web page testing
│   │   ├── streaming.py       # Jellyfin video streaming testing
│   │   └── voip_sipp.py       # SIPp VoIP call testing
│   └── utils/
│       ├── __init__.py
│       ├── db.py              # PostgreSQL connection pool & queries
│       ├── aggregator.py      # Metric aggregation & percentiles
│       ├── config_validator.py# Configuration validation engine
│       ├── unit_converter.py  # Unit normalization for comparisons
│       ├── error_logger.py    # Centralized error logging
│       └── uuid_generator.py  # UUID4 generation
├── docker/
│   └── init_db.sql            # Database schema initialization
├── debian/                    # Debian package structure
│   ├── DEBIAN/
│   │   ├── control            # Package metadata
│   │   ├── postinst           # Post-install script
│   │   ├── prerm              # Pre-removal script
│   │   └── postrm             # Post-removal script
│   └── usr/local/bin/
│       ├── loadtest           # CLI entry point wrapper
│       └── loadtest-cleanup   # Cleanup wrapper
├── logo/                      # UI logo assets
└── docs/                      # Documentation (this directory)
```

---

## Component Details

### orchestrate.py

The orchestrator is the main entry point for CLI mode. It follows an 8-step pipeline:

1. **Load & validate configuration** - Uses `ConfigValidator` to catch errors early
2. **Setup report path** - Creates the output directory
3. **Setup Docker infrastructure** - Initializes Swarm, overlay network, and PostgreSQL
4. **Process scenarios** - Generates UUIDs, inserts scenario records, deploys services
5. **Wait for workers** - Calculates absolute end time across all scenarios
6. **Monitor execution** - Polls service status every 10 seconds
7. **Cleanup services** - Removes Swarm services and exited containers
8. **Export results** - Final CSV export from PostgreSQL

**Key functions:**
- `init_docker_swarm()` - Initializes Swarm with `--advertise-addr 127.0.0.1`
- `ensure_docker_network()` - Creates overlay network with bridge fallback
- `start_postgres_container()` - Starts PostgreSQL 16 Alpine with volume persistence
- `deploy_test_service()` - Creates a Docker Swarm service per scenario
- `calculate_scenario_end_time()` - Computes the absolute end time across all scenarios, accounting for protocol-specific durations
- `periodic_export()` - Background thread that exports CSV every 5 seconds

### worker.py

Workers run inside Docker containers as `python3 -m src.worker <scenario_id>`. Each worker:

1. Reads scenario configuration from the `SCENARIO_CONFIG` environment variable
2. Creates a `ScenarioScheduler` instance
3. Schedules the scenario (once or recurring)
4. Waits for completion based on mode and timing
5. Finalizes the scenario (evaluates scenario-scope expectations, saves summary)
6. Shuts down the scheduler

### scheduler.py - ScenarioScheduler

The scheduler wraps APScheduler's `BackgroundScheduler` with scenario-aware lifecycle management:

- **Job scheduling** - Uses `DateTrigger` for one-time jobs, `IntervalTrigger` for recurring
- **Job tracking** - Maintains maps of scenario IDs to job IDs, end times, and configs
- **Running job counting** - Thread-safe tracking via `EVENT_JOB_SUBMITTED` / `EVENT_JOB_EXECUTED` listeners
- **Completion detection** - `is_scenario_complete()` checks both time elapsed and running job count
- **Completion waiting** - `wait_for_scenario()` uses `threading.Event` for blocking waits
- **Finalization** - `finalize_scenario()` evaluates scenario-scope expectations and saves aggregated summaries

**Thread pool:** 3 threads via `ThreadPoolExecutor`, with `max_instances=5` per job and 1-hour misfire grace time.

### gui.py

PyQt5 desktop application with a dark theme (black/crimson color scheme). Provides:

- Scenario editor with protocol-specific parameter forms
- Schedule configuration (once/recurring/scheduled)
- Expectation builder with metric/operator/value/unit fields
- Test runner with live output console
- Results viewer for CSV files

---

## Docker Infrastructure

### Docker Image (Dockerfile)

The worker Docker image is based on `ubuntu:22.04` and includes:

- Python 3 with pip
- iperf3 for speed testing
- Playwright Chromium dependencies (X11/rendering libraries)
- PostgreSQL client libraries (libpq for psycopg2)
- tshark for RTP packet capture
- SIPp built from source (with SSL, PCAP, SCTP, GSL)
- SIPp scenario XML files with RTD tracing patches

### Docker Swarm Services

Each scenario is deployed as a Swarm service:

```
Service: loadtest-{scenario_id[:8]}
  Replicas: 1
  Network: loadtest-network
  Capabilities: NET_RAW, NET_ADMIN
  Restart: none
  Command: python3 -m src.worker {scenario_id}
  Environment:
    SCENARIO_ID, SCENARIO_CONFIG (JSON),
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    REPORT_PATH
```

### Network Architecture

```
Host Machine
  ├── loadtest-network (overlay, attachable)
  │   ├── db-container (PostgreSQL 16, port 5432)
  │   ├── loadtest-{id1} (worker service)
  │   ├── loadtest-{id2} (worker service)
  │   └── ...
  └── Docker Swarm Manager (127.0.0.1)
```

### PostgreSQL Container

- Image: `postgres:16-alpine`
- Volume: `load-test` (persistent data)
- Port: `5432` (host-mapped)
- Init script: `docker/init_db.sql` (schema creation)
- Network: `loadtest-network`

---

## Database Design

### Schema: `load_test`

#### scenarios
| Column          | Type    | Description                   |
|-----------------|---------|-------------------------------|
| scenario_id     | UUID PK | Unique scenario identifier    |
| protocol        | VARCHAR | Protocol name                 |
| config_snapshot | JSONB   | Full configuration at runtime |

#### test_runs
| Column      | Type      | Description                   |
|-------------|-----------|-------------------------------|
| run_id      | UUID PK   | Unique run identifier         |
| scenario_id | UUID FK   | Reference to scenario         |
| start_time  | TIMESTAMP | When the run started          |
| worker_node | VARCHAR   | Container hostname            |

#### raw_metrics
| Column       | Type      | Description                   |
|--------------|-----------|-------------------------------|
| id           | UUID PK   | Unique metric entry ID        |
| run_id       | UUID FK   | Reference to test run         |
| metric_name  | VARCHAR   | Metric name (e.g., `latency`) |
| metric_value | VARCHAR   | Measured value (stored as string) |
| timestamp    | TIMESTAMP | When the metric was collected |

#### results_log
| Column         | Type    | Description                         |
|----------------|---------|-------------------------------------|
| id             | UUID PK | Unique result entry ID              |
| run_id         | UUID FK | Reference to test run               |
| metric_name    | VARCHAR | Metric being evaluated              |
| expected_value | VARCHAR | Threshold (e.g., "100 mbps")        |
| measured_value | VARCHAR | Actual measured value               |
| status         | VARCHAR | PASS, FAIL, or ERROR                |
| scope          | VARCHAR | per_iteration or scenario           |

#### scenario_summary
| Column            | Type      | Description                    |
|-------------------|-----------|--------------------------------|
| id                | UUID PK   | Unique summary entry ID        |
| scenario_id       | UUID FK   | Reference to scenario          |
| metric_name       | VARCHAR   | Metric name                    |
| sample_count      | INTEGER   | Number of data points          |
| avg_value         | NUMERIC   | Mean value                     |
| min_value         | NUMERIC   | Minimum value                  |
| max_value         | NUMERIC   | Maximum value                  |
| percentile        | INTEGER   | Percentile number (1-99)       |
| percentile_result | NUMERIC   | Calculated percentile value    |
| stddev_value      | NUMERIC   | Standard deviation             |
| aggregated_at     | TIMESTAMP | When summary was computed      |

**Unique constraint:** `(scenario_id, metric_name)` on `scenario_summary` enables UPSERT.

### Connection Pool

The `db.py` module uses `psycopg2.pool.ThreadedConnectionPool`:
- Min connections: 2
- Max connections: 10
- Thread-safe via `_pool_lock`
- Context manager with auto-commit/rollback

---

## Execution Pipeline

### End-to-End Flow

```
User starts test (GUI or CLI)
    │
    ▼
orchestrate.py: validate config
    │
    ▼
Init Docker Swarm + overlay network
    │
    ▼
Start PostgreSQL container
    │
    ▼
For each enabled scenario:
    ├── Generate UUID
    ├── INSERT INTO scenarios
    └── docker service create → Worker container
                                    │
                                    ▼
                              worker.py starts
                                    │
                                    ▼
                              ScenarioScheduler
                              schedules job(s)
                                    │
                                    ▼
                              APScheduler fires job
                                    │
                                    ▼
                              _execute_test()
                              ├── INSERT test_run
                              ├── Call protocol handler
                              │   └── Returns List[Result]
                              ├── INSERT raw_metrics (batch)
                              └── Evaluate per_iteration expectations
                                  └── INSERT results_log
                                    │
                                    ▼
                              (repeat for recurring)
                                    │
                                    ▼
                              finalize_scenario()
                              ├── Evaluate scenario expectations
                              ├── save_scenario_summary()
                              └── Cleanup in-memory state
    │
    ▼
orchestrate.py monitors services
    │
    ▼
All services complete/timeout
    │
    ▼
Remove services + cleanup containers
    │
    ▼
Final CSV export
```

### Timing Calculation

The orchestrator calculates an absolute end time by analyzing all enabled scenarios:

- **Speed test:** `scenario_end + (duration * 3 + 10)` seconds
- **Streaming:** `scenario_end + sum(video_runtimes)` (fetched from Jellyfin API)
- **Web browsing:** `scenario_end + (num_urls * 30)` seconds
- **VoIP:** `scenario_end + (num_calls * call_duration + 60) * num_targets` seconds

For recurring scenarios, `scenario_end = start_time + duration_hours`.

---

## Test Module Internals

### Speed Test (`speed_test.py`)

Uses `iperf3` via subprocess with JSON output (`-J` flag).

**Test sequence per target:**
1. TCP download: `iperf3 -c host -p port -t dur -J -P 8 -O 5 -R` (reverse mode)
2. Ping latency: `ping -c 5 -W 5 host`
3. 5s pause
4. TCP upload: `iperf3 -c host -p port -t dur -J -P 8 -O 5`
5. 5s pause
6. UDP jitter: `iperf3 -c host -p port -t dur -J -u`

**Flags:** 8 parallel streams (`-P 8`), 5-second omit period (`-O 5`), 10s connect timeout.

**Output:** `SpeedTestResult` dataclass with download_speed (Mbps), upload_speed (Mbps), jitter (ms), latency (ms).

### Web Browsing (`web_browsing.py`)

Uses Playwright's synchronous API to launch Chromium and navigate to URLs.

**Features:**
- Cache disabling via CDP `Network.setCacheDisabled`
- Navigation Performance API for precise timing metrics
- Response event tracking for resource count and redirect detection
- Parallel mode with `ThreadPoolExecutor` (each URL gets its own browser)

**Output:** `WebBrowsingResult` dataclass per URL.

### Streaming (`streaming.py`)

Full Jellyfin browser automation:

1. Fetches `ServerId` and `UserId` from Jellyfin API
2. Injects `jellyfin_credentials` into browser localStorage
3. Routes all server requests with `X-Emby-Token` header
4. Navigates to item detail page and clicks Play button
5. Monitors `<video>` element via JavaScript evaluation loop (0.5s intervals)
6. Tracks buffer levels, resolution changes, rebuffering events
7. Calculates network metrics from request/response interception
8. Monitors until video `ended` event, URL navigation away, or 2-hour ceiling

**Output:** `StreamingResult` dataclass with 22 metrics per video.

### VoIP SIPp (`voip_sipp.py`)

SIPp test execution with optional tshark RTP capture:

1. Locates SIPp binary (system paths or bundled)
2. Builds target URL with media-type port mapping
3. Constructs SIPp command with scenario file, call params, and trace flags
4. Starts tshark UDP capture in background (`-f "udp"`)
5. Runs SIPp with non-interactive flags (`-nd`, `-nostdin`)
6. Parses SIPp trace files:
   - `trace_stat` CSV for call success/failure counts
   - `trace_rtt` CSV for RTT measurements and SIP response jitter
7. Parses tshark `rtp,streams` analysis for RTP metrics
8. Classifies RTP streams as audio/video by codec payload name

**Scenario files:** `sipp/sipp_scenarios/pfca_uac_apattern.xml` (audio) and `pfca_uac_vpattern.xml` (video). The Dockerfile patches these with `rtd="true"` for RTT tracing.

---

## Metric Collection & Evaluation

### Metric Flow

```
Test Module returns List[Result]
    │
    ▼
_extract_metrics(result, configured_metrics)
    → Extracts numeric fields from dataclass/dict
    → Filters to only metrics listed in expectations
    │
    ▼
insert_raw_metrics_batch(run_id, metrics)
    → Writes to raw_metrics table
    │
    ▼
_evaluate_expectations(run_id, scenario_id, expectations, scope)
    │
    ├── per_iteration scope:
    │   → Evaluates each result set individually
    │   → normalize_for_comparison(measured, expected, unit, metric)
    │   → _compare_values(measured, operator, expected)
    │   → insert_result_log(PASS/FAIL/ERROR)
    │
    └── scenario scope (at finalization):
        → get_aggregated_value(scenario_id, metric, aggregation)
        → Queries all raw_metrics across runs
        → Applies aggregation function (avg/min/max/p50/p99/etc)
        → normalize_for_comparison + _compare_values
        → insert_result_log
```

### Error Sentinel

A metric value of `-1` indicates a measurement error (e.g., unreachable host, parse failure). These values:
- Are skipped during aggregation (filtered out)
- Result in `ERROR` status in results_log (not PASS/FAIL)

---

## Unit Conversion System

The `unit_converter.py` module handles normalization for fair comparisons between measured and expected values.

### Standard Units

| Category | Standard Unit | Native Examples                           |
|----------|---------------|-------------------------------------------|
| Speed    | Mbps          | download_speed (Mbps), est_bitrate_bps (bps), audio_rtp_bitrate_kbps (kbps) |
| Time     | ms            | latency (ms), playback_seconds (seconds), startup_latency_sec (seconds) |
| Count    | count         | resource_count, rebuffer_events, call_success |

### Conversion Flow

```
normalize_for_comparison(measured_value, expected_value, expected_unit, metric_name)
    │
    ├── Look up native unit from METRIC_NATIVE_UNITS
    │   e.g., "playback_seconds" → "seconds"
    │
    ├── convert_to_standard(measured_value, native_unit, metric_name)
    │   e.g., 120 seconds → 120,000 ms
    │
    ├── convert_to_standard(expected_value, expected_unit, metric_name)
    │   e.g., 5 seconds → 5,000 ms
    │
    └── Return (measured_ms, expected_ms) for comparison
```

---

## Error Handling

### Error Logger

The `error_logger.py` module provides centralized error logging:

- Writes to `error_log.txt` in the results directory
- Format: `TIMESTAMP | ERROR | [module.function] ExceptionType: message | Context: details`
- Singleton logger initialized once per process
- Fallback to current directory if not explicitly initialized

### Error Propagation

- Test module errors are caught and logged; error sentinel values (`-1`) are returned
- Scheduler catches exceptions in `_execute_test()` to prevent job crashes
- Worker handles scheduling errors and ensures `finalize_scenario()` is always called
- Orchestrator catches `KeyboardInterrupt` for graceful shutdown

---

## Configuration Validation

The `ConfigValidator` class performs comprehensive validation:

### Validation Layers

1. **Structural** - Required fields, correct types, non-empty values
2. **Protocol-specific** - Required/optional parameters per protocol
3. **URL format** - `host:port` for speed_test, hostname for VoIP, full URL for web_browsing
4. **Schedule logic** - Recurring mode requires interval/duration; duration > interval
5. **Expectation validity** - Valid metrics per protocol, valid operators/units/scopes
6. **Cross-field** - Speed test execution time vs. interval (overlap detection)
7. **VoIP media type** - Audio metrics only with audio type, video metrics only with video type
8. **Unit-metric mapping** - Validates unit category matches metric category (speed/time/count)
9. **Temporal** - Scheduled start times must be in the future
10. **Unknown fields** - Warns about unrecognized configuration keys

---

## Packaging & Distribution

### Debian Package (`build_deb.sh`)

The build script creates `loadtestframework.deb`:

1. Copies application files to `debian/opt/loadtestframework/`
2. Builds SIPp and copies scenario files
3. Sets correct permissions (644 for data, 755 for scripts/dirs)
4. Runs `dpkg-deb --build` to create the package

### Package Scripts

- **postinst** - Sets permissions, creates results directory, prompts for setup
- **prerm** - Cleanup before removal
- **postrm** - Cleanup after removal

### Entry Points

- `/usr/local/bin/loadtest` - Main CLI wrapper (activates venv, dispatches to GUI or orchestrator)
- `/usr/local/bin/loadtest-cleanup` - Cleanup wrapper

---

## Extending the Framework

### Adding a New Test Protocol

1. **Create test module** in `src/test_modules/new_protocol.py`:
   - Define a result dataclass with numeric metric fields
   - Implement `run_new_protocol_test(parameters: dict) -> list[ResultClass]`

2. **Register the handler** in `src/scheduler.py`:
   ```python
   from src.test_modules.new_protocol import run_new_protocol_test

   PROTOCOL_HANDLERS = {
       ...
       "new_protocol": run_new_protocol_test,
   }
   ```

3. **Add validation rules** in `src/utils/config_validator.py`:
   - Add to `VALID_PROTOCOLS`
   - Add protocol parameters to `PROTOCOL_PARAMS`
   - Add valid metrics to `PROTOCOL_METRICS`

4. **Register metric categories** in `src/utils/unit_converter.py`:
   - Add entries to `METRIC_CATEGORIES`
   - Add entries to `METRIC_NATIVE_UNITS`

5. **Update the Dockerfile** if the protocol needs additional system dependencies.

6. **Handle timing** in `orchestrate.py` `calculate_scenario_end_time()` for the new protocol.

### Adding a New Metric to an Existing Protocol

1. Add the field to the result dataclass in the test module
2. Add the metric name to `PROTOCOL_METRICS` in `config_validator.py`
3. Add the metric to `METRIC_CATEGORIES` and `METRIC_NATIVE_UNITS` in `unit_converter.py`
4. The metric will automatically be:
   - Extracted if it matches an expectation
   - Written to `raw_metrics`
   - Available for aggregation and evaluation

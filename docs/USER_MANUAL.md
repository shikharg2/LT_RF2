# LoadTest Framework - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Getting Started](#getting-started)
5. [GUI Mode](#gui-mode)
6. [CLI Mode](#cli-mode)
7. [Configuration Reference](#configuration-reference)
8. [Test Protocols](#test-protocols)
9. [Scheduling](#scheduling)
10. [Expectations & Evaluation](#expectations--evaluation)
11. [Results & Reports](#results--reports)
12. [Cleanup & Maintenance](#cleanup--maintenance)
13. [Troubleshooting](#troubleshooting)

---

## Introduction

The LoadTest Framework is a comprehensive load testing tool that supports four network testing protocols:

- **Speed Test** - Bandwidth measurement using iperf3 (download, upload, latency, jitter)
- **Web Browsing** - Page load performance using Playwright/Chromium (load time, TTFB, DOM loaded)
- **Video Streaming** - Jellyfin video playback quality (buffering, bitrate, rebuffer events)
- **VoIP (SIPp)** - Voice/video over IP call testing with SIP signaling and RTP media analysis

Tests run inside Docker Swarm services for parallel, isolated execution. Results are stored in a PostgreSQL database and exported to CSV.

---

## System Requirements

| Component         | Requirement                          |
|-------------------|--------------------------------------|
| Operating System  | Ubuntu 22.04+ (amd64)                |
| Python            | 3.8+                                 |
| Docker            | Docker Engine with Swarm mode        |
| RAM               | 4 GB minimum, 8 GB recommended       |
| Disk              | 2 GB free for Docker images + results |
| Network           | Access to test target servers         |

### Additional Dependencies (installed by setup)

- Docker Engine + Compose plugin
- Playwright + Chromium browser
- SIPp (built from source with SSL, PCAP, SCTP, GSL)
- tshark (for VoIP RTP media capture)
- PostgreSQL 16 (runs as Docker container)
- iperf3 (included in Docker image)

---

## Installation

### Install from .deb Package

```bash
# Build the package (from source)
./build_deb.sh

# Install
mv loadtestframework.deb /tmp/
cd /tmp/
sudo apt install ./loadtestframework.deb

# Run first-time setup (installs Docker, Python deps, SIPp, builds Docker image)
sudo loadtest --setup
```

### What Setup Does

The `sudo loadtest --setup` command performs the following steps:

1. Installs Docker Engine from the official repository
2. Creates a Python virtual environment at `/opt/loadtestframework/.venv`
3. Installs Python dependencies (Playwright, psycopg2, APScheduler, PyQt5)
4. Installs Playwright Chromium browser
5. Builds SIPp from source with SSL, PCAP, SCTP, and GSL support
6. Initializes Docker Swarm (advertise address: `127.0.0.1`)
7. Creates the `loadtest-network` Docker overlay network
8. Builds the `loadtest:latest` Docker image

Setup only runs once. A marker file `.setup_complete` is created after successful completion.

---

## Getting Started

### Launch the GUI

```bash
loadtest
```

### Run in CLI Mode

```bash
loadtest /path/to/config.json
```

### View Help

```bash
loadtest --help
```

---

## GUI Mode

The GUI provides a visual interface for:

- **Creating and editing test configurations** - Add scenarios with protocol-specific parameters
- **Managing scenario schedules** - Set one-time or recurring test execution
- **Defining expectations** - Configure pass/fail thresholds for metrics
- **Running tests** - Execute the orchestrator and monitor progress
- **Viewing results** - Browse CSV results and review pass/fail status

The GUI saves configurations to `configurations/main.json` and launches the orchestrator when you run tests.

---

## CLI Mode

CLI mode runs the orchestrator directly with a configuration file:

```bash
loadtest my_config.json
```

The orchestrator follows this workflow:

1. Validates the configuration file
2. Sets up the report output directory
3. Initializes Docker Swarm and overlay network
4. Starts a PostgreSQL container for metrics storage
5. Deploys a Docker Swarm service per enabled scenario
6. Monitors running services until completion or timeout
7. Exports results to CSV files
8. Cleans up services and containers

---

## Configuration Reference

Configuration files use JSON format. The top-level structure is:

```json
{
  "global_settings": {
    "report_path": "./results/"
  },
  "scenarios": [ ... ]
}
```

### Global Settings

| Field         | Type   | Required | Description                          |
|---------------|--------|----------|--------------------------------------|
| `report_path` | string | Yes      | Directory for CSV result output      |
| `log_level`   | string | No       | Log verbosity: DEBUG, INFO, WARNING, ERROR |

### Scenario Structure

```json
{
  "id": "my_test",
  "description": "Description of the test",
  "enabled": true,
  "protocol": "speed_test",
  "schedule": { ... },
  "parameters": { ... },
  "expectations": [ ... ]
}
```

| Field          | Type    | Required | Description                          |
|----------------|---------|----------|--------------------------------------|
| `id`           | string  | Yes      | Unique identifier for the scenario   |
| `description`  | string  | No       | Human-readable description           |
| `enabled`      | boolean | Yes      | Whether the scenario is active       |
| `protocol`     | string  | Yes      | One of: `speed_test`, `web_browsing`, `streaming`, `voip_sipp` |
| `schedule`     | object  | Yes      | When and how often to run            |
| `parameters`   | object  | Yes      | Protocol-specific test parameters    |
| `expectations` | array   | Yes      | Pass/fail threshold definitions      |

---

## Test Protocols

### Speed Test

Measures network bandwidth using iperf3 against target servers.

**Parameters:**

| Parameter    | Type       | Required | Description                           |
|--------------|------------|----------|---------------------------------------|
| `target_url` | string[]   | Yes      | List of `host:port` iperf3 servers    |
| `duration`   | integer    | No       | Duration per test in seconds (min: 1) |

**How it works:**
1. Runs iperf3 TCP download test (reverse mode, 8 parallel streams)
2. Measures latency via ICMP ping
3. Runs iperf3 TCP upload test (8 parallel streams)
4. Runs iperf3 UDP test for jitter measurement

**Available Metrics:**

| Metric           | Unit | Description                       |
|------------------|------|-----------------------------------|
| `download_speed` | Mbps | TCP download throughput           |
| `upload_speed`   | Mbps | TCP upload throughput             |
| `latency`        | ms   | Average ICMP ping RTT            |
| `jitter`         | ms   | UDP jitter from iperf3           |

**Example:**
```json
{
  "id": "speed_test_1",
  "enabled": true,
  "protocol": "speed_test",
  "schedule": { "mode": "recurring", "start_time": "immediate", "interval_minutes": 60, "duration_hours": 6 },
  "parameters": {
    "target_url": ["192.168.1.100:5201"],
    "duration": 30
  },
  "expectations": [
    { "metric": "download_speed", "operator": "gte", "value": 100, "unit": "mbps", "aggregation": "avg", "evaluation_scope": "scenario" }
  ]
}
```

> **Note:** For recurring speed tests, ensure the interval is longer than the estimated execution time (`3 x duration + 15s overhead`) to avoid overlapping tests.

---

### Web Browsing

Measures web page load performance using a headless Chromium browser (Playwright).

**Parameters:**

| Parameter           | Type     | Required | Description                              |
|---------------------|----------|----------|------------------------------------------|
| `target_url`        | string[] | Yes      | List of full URLs (`http://` or `https://`) |
| `headless`          | boolean  | No       | Run browser in headless mode (default: true) |
| `disable_cache`     | boolean  | No       | Disable browser cache (default: false)   |

**Available Metrics:**

| Metric                | Unit  | Description                              |
|-----------------------|-------|------------------------------------------|
| `page_load_time`      | ms    | Total page load time (loadEventEnd)      |
| `ttfb`                | ms    | Time to first byte                       |
| `dom_content_loaded`  | ms    | DOM content loaded event time            |
| `http_response_code`  | code  | HTTP status code of main document        |
| `resource_count`      | count | Number of resources loaded               |
| `redirect_count`      | count | Number of HTTP redirects                 |

**Example:**
```json
{
  "id": "web_test",
  "enabled": true,
  "protocol": "web_browsing",
  "schedule": { "mode": "once", "start_time": "immediate" },
  "parameters": {
    "target_url": ["https://www.example.com"],
    "headless": true,
    "disable_cache": true
  },
  "expectations": [
    { "metric": "page_load_time", "operator": "lte", "value": 5000, "unit": "ms", "aggregation": "p90", "evaluation_scope": "scenario" }
  ]
}
```

---

### Video Streaming (Jellyfin)

Tests video streaming quality by playing videos from a Jellyfin media server through a real browser.

**Parameters:**

| Parameter            | Type     | Required | Description                              |
|----------------------|----------|----------|------------------------------------------|
| `server_url`         | string   | Yes      | Jellyfin server URL (e.g., `http://host:8096`) |
| `api_key`            | string   | Yes      | Jellyfin API key for authentication      |
| `item_ids`           | string[] | Yes      | List of Jellyfin media item IDs          |
| `headless`           | boolean  | No       | Run browser in headless mode (default: true) |
| `disable_cache`      | boolean  | No       | Disable browser cache (default: false)   |
| `parallel_browsing`  | boolean  | No       | Play videos in parallel (default: false) |
| `aggregate`          | boolean  | No       | Aggregate results into single entry (default: false) |

**Available Metrics:**

| Metric                    | Unit    | Description                              |
|---------------------------|---------|------------------------------------------|
| `initial_buffer_time`     | ms      | Time until video starts playing          |
| `startup_latency_sec`     | seconds | Startup latency in seconds               |
| `test_wall_seconds`       | seconds | Total wall clock time of the test        |
| `playback_seconds`        | seconds | Total seconds of video played            |
| `active_playback_seconds` | seconds | Playback time excluding buffering        |
| `rebuffer_events`         | count   | Number of rebuffering events             |
| `rebuffer_ratio`          | ratio   | Ratio of rebuffer time to playback time  |
| `min_buffer`              | seconds | Minimum buffer level observed            |
| `max_buffer`              | seconds | Maximum buffer level observed            |
| `avg_buffer`              | seconds | Average buffer level                     |
| `resolution_switches`     | count   | Number of quality/resolution changes     |
| `segments_fetched`        | count   | Number of video segments fetched         |
| `non_200_segments`        | count   | Segments with non-200 HTTP responses     |
| `avg_segment_latency_sec` | seconds | Average latency for segment fetches      |
| `max_segment_latency_sec` | seconds | Maximum segment fetch latency            |
| `est_bitrate_bps`         | bps     | Estimated bitrate                        |
| `error_count`             | count   | Total errors encountered                 |
| `download_speed`          | Mbps    | Average download speed during test       |
| `upload_speed`            | Mbps    | Average upload speed during test         |
| `latency`                 | ms      | Average request-response RTT             |
| `jitter`                  | ms      | Standard deviation of latency            |

---

### VoIP (SIPp)

Tests Voice/Video over IP using SIPp for SIP signaling and tshark for RTP media capture.

**Parameters:**

| Parameter          | Type     | Required | Description                              |
|--------------------|----------|----------|------------------------------------------|
| `target_url`       | string[] | Yes      | List of SIP server hostnames/IPs         |
| `number_of_calls`  | integer  | No       | Number of calls to place (min: 1)        |
| `call_duration`    | integer  | No       | Duration per call in seconds (min: 1)    |
| `type`             | string   | No       | Media type: `none`, `audio`, `video`     |
| `transport`        | string   | No       | Transport protocol: `udp`, `tcp`         |

**Media Type Routing:**
- `none` - SIP signaling only, connects to target IP default port
- `audio` - Audio media, connects to target IP port 5061
- `video` - Video media, connects to target IP port 5062

**Available Metrics:**

| Metric                       | Unit  | Description                              |
|------------------------------|-------|------------------------------------------|
| `call_success`               | count | Number of successful calls               |
| `call_setup_time`            | ms    | Average call setup time (RTT)            |
| `failed_calls`               | count | Number of failed calls                   |
| `retransmissions`            | count | SIP message retransmissions              |
| `timeout_errors`             | count | Connection timeout errors                |
| `avg_rtt`                    | ms    | Average SIP round-trip time              |
| `min_rtt`                    | ms    | Minimum RTT                              |
| `max_rtt`                    | ms    | Maximum RTT                              |
| `sip_response_jitter`        | ms    | SIP response time variation              |
| `audio_rtp_packets`          | count | Audio RTP packets observed               |
| `audio_rtp_packet_loss`      | count | Audio packets lost                       |
| `audio_rtp_packet_loss_rate` | ratio | Audio packet loss ratio (0-1)            |
| `audio_rtp_jitter`           | ms    | Audio RTP interarrival jitter            |
| `audio_rtp_bitrate_kbps`     | kbps  | Audio RTP bitrate                        |
| `video_rtp_packets`          | count | Video RTP packets observed               |
| `video_rtp_packet_loss`      | count | Video packets lost                       |
| `video_rtp_packet_loss_rate` | ratio | Video packet loss ratio (0-1)            |
| `video_rtp_jitter`           | ms    | Video RTP interarrival jitter            |
| `video_rtp_bitrate_kbps`     | kbps  | Video RTP bitrate                        |
| `jitter`                     | ms    | Overall RTP interarrival jitter          |
| `media_streams_observed`     | count | Number of RTP streams detected           |
| `media_packets_sent`         | count | Total media packets sent                 |
| `media_packets_received`     | count | Total media packets received             |
| `media_packet_loss`          | count | Total media packet loss                  |
| `media_packet_loss_rate`     | ratio | Overall media loss ratio                 |

> **Note:** Audio-only metrics require `type: "audio"`, video-only metrics require `type: "video"`. Media metrics (RTP) require tshark to be available.

---

## Scheduling

Each scenario has a `schedule` section that controls when and how often it runs.

### One-Time Execution

```json
{
  "mode": "once",
  "start_time": "immediate"
}
```

Or scheduled for a specific time:

```json
{
  "mode": "once",
  "start_time": "2025-06-15T10:00:00+05:30"
}
```

### Recurring Execution

```json
{
  "mode": "recurring",
  "start_time": "immediate",
  "interval_minutes": 30,
  "duration_hours": 4
}
```

| Field              | Type          | Required          | Description                              |
|--------------------|---------------|-------------------|------------------------------------------|
| `mode`             | string        | Yes               | `once` or `recurring`                    |
| `start_time`       | string        | Yes               | `immediate` or ISO 8601 datetime         |
| `interval_minutes` | number        | Recurring only    | Minutes between test runs (must be > 0)  |
| `duration_hours`   | number        | Recurring only    | Total duration in hours (must be > interval) |

---

## Expectations & Evaluation

Expectations define pass/fail thresholds for collected metrics. Each expectation is evaluated either per iteration or across the entire scenario.

### Expectation Structure

```json
{
  "metric": "download_speed",
  "operator": "gte",
  "value": 100,
  "unit": "mbps",
  "aggregation": "avg",
  "evaluation_scope": "scenario"
}
```

| Field              | Type   | Description                                          |
|--------------------|--------|------------------------------------------------------|
| `metric`           | string | Metric name (protocol-specific, see tables above)    |
| `operator`         | string | Comparison operator                                  |
| `value`            | number | Threshold value                                      |
| `unit`             | string | Unit of the expected value                           |
| `aggregation`      | string | How to aggregate metric values                       |
| `evaluation_scope` | string | When to evaluate: `per_iteration` or `scenario`     |

### Comparison Operators

| Operator | Description              |
|----------|--------------------------|
| `lt`     | Less than                |
| `lte`    | Less than or equal to    |
| `gt`     | Greater than             |
| `gte`    | Greater than or equal to |
| `eq`     | Equal to                 |
| `neq`    | Not equal to             |

### Aggregation Functions

| Function      | Description                              |
|---------------|------------------------------------------|
| `avg`         | Average (mean) of all values             |
| `min`         | Minimum value                            |
| `max`         | Maximum value                            |
| `stddev`      | Standard deviation                       |
| `p1` - `p99`  | Percentile (e.g., `p50` for median, `p95`, `p99`) |

### Evaluation Scopes

- **`per_iteration`** - Each test run is evaluated individually against the threshold. Results are written per URL/target.
- **`scenario`** - Values are aggregated across all runs in the scenario, then evaluated once at finalization.

### Unit Conversions

The framework automatically converts between units for comparison. Measured values (in their native unit from the test module) and expected values (in the configured unit) are both normalized to standard units before comparison.

**Speed units:** `bps`, `kbps`, `mbps`, `gbps`, `Bps`, `KBps`, `MBps`, `GBps`
**Time units:** `ns`, `us`, `ms`, `s`, `sec`, `seconds`, `min`, `minutes`
**Count units:** `count`, `code`, `ratio`

---

## Results & Reports

### Output Files

Results are exported as CSV files to the configured `report_path` directory:

| File                   | Description                                |
|------------------------|--------------------------------------------|
| `scenarios.csv`        | Scenario configurations                    |
| `test_runs.csv`        | Individual test run records                |
| `raw_metrics.csv`      | All collected metric values                |
| `results_log.csv`      | Pass/fail evaluation results               |
| `scenario_summary.csv` | Aggregated statistics per scenario         |
| `error_log.txt`        | Error log with timestamps and context      |

### CSV Export Behavior

- Results are exported periodically (every 5 seconds) during test execution
- A final export occurs after all tests complete
- Files are overwritten each export cycle (not appended)

### Database Schema

Results are stored in a PostgreSQL database (`load_test` schema) with the following tables:

- **scenarios** - Scenario UUID, protocol, full config snapshot
- **test_runs** - Run UUID, scenario reference, start time, worker node
- **raw_metrics** - Individual metric measurements with timestamps
- **results_log** - Expectation evaluation results (PASS/FAIL/ERROR)
- **scenario_summary** - Aggregated statistics (avg, min, max, percentile, stddev)

---

## Cleanup & Maintenance

### Cleanup Docker Resources

```bash
loadtest-cleanup
```

This removes all loadtest-related Docker Swarm services, containers (except `db-container`), and networks.

### Cleanup Options

```bash
loadtest-cleanup --images      # Also remove loadtest Docker images
loadtest-cleanup --no-prune    # Skip pruning unused Docker resources
```

### Full Uninstall

```bash
sudo apt remove loadtestframework
```

The package removal scripts clean up systemd services and wrapper scripts. The Docker resources and database container may need manual cleanup using `loadtest-cleanup --images`.

---

## Troubleshooting

### Setup Fails

- Ensure you are running with `sudo`
- Check internet connectivity (Docker and SIPp require downloads)
- If re-running setup, delete `/opt/loadtestframework/.setup_complete` first

### Tests Don't Start

- Verify Docker Swarm is active: `docker info --format '{{.Swarm.LocalNodeState}}'`
- Check the overlay network exists: `docker network ls | grep loadtest`
- Ensure the Docker image is built: `docker images | grep loadtest`

### PostgreSQL Connection Issues

- Check if `db-container` is running: `docker ps | grep db-container`
- Verify port 5432 is accessible: `docker exec db-container pg_isready -U postgres`

### Speed Test Failures

- Ensure the iperf3 server is reachable on the specified port
- Check firewall rules for TCP/UDP on the target port

### Web Browsing Failures

- URLs must start with `http://` or `https://`
- If Chromium crashes, try increasing Docker container memory limits

### VoIP Test Failures

- SIPp must be installed (happens during setup)
- For RTP media metrics, tshark must be available in the Docker container
- Ensure the SIP server (UAS) is running and reachable

### No Results Generated

- Check `error_log.txt` in the results directory for detailed error messages
- Ensure the `report_path` directory is writable
- Verify the PostgreSQL container is healthy

### Force Re-setup

```bash
sudo rm /opt/loadtestframework/.setup_complete
sudo loadtest --setup
```

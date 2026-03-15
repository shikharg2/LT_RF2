#!/usr/bin/env python3
"""
LoadTest Framework - Architecture Diagrams

Generates architecture and flow diagrams using matplotlib.
Run: python3 docs/diagrams.py

Output: PNG files in docs/ directory
Requirements: pip install matplotlib
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ──────────────────────────────────────────────────────────────
# Color palette
# ──────────────────────────────────────────────────────────────
COLORS = {
    "bg": "#0a0a12",
    "card": "#141420",
    "card_border": "#2a2a3a",
    "primary": "#9e3535",
    "primary_light": "#c44a4a",
    "secondary": "#1a3a5c",
    "secondary_light": "#2a5a8c",
    "success": "#1b8a3e",
    "warning": "#d47800",
    "text": "#d8d8dc",
    "text_muted": "#808088",
    "connector": "#4a4a5a",
    "docker_blue": "#2496ed",
    "postgres": "#336791",
    "python": "#3776ab",
}


def _setup_figure(width, height, title):
    """Create a figure with dark background."""
    fig, ax = plt.subplots(1, 1, figsize=(width, height))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title(title, color=COLORS["text"], fontsize=18, fontweight="bold", pad=20)
    return fig, ax


def _draw_box(ax, x, y, w, h, label, color, sublabel=None, fontsize=10):
    """Draw a rounded rectangle with label."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3",
        facecolor=color,
        edgecolor=COLORS["card_border"],
        linewidth=1.5,
        alpha=0.9,
    )
    ax.add_patch(box)
    text_y = y + h / 2 + (1.5 if sublabel else 0)
    ax.text(x + w / 2, text_y, label, ha="center", va="center",
            color=COLORS["text"], fontsize=fontsize, fontweight="bold")
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 2, sublabel, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=fontsize - 2)


def _draw_arrow(ax, x1, y1, x2, y2, label=None, color=None):
    """Draw an arrow between two points."""
    arrow_color = color or COLORS["connector"]
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="->",
            color=arrow_color,
            linewidth=1.5,
            connectionstyle="arc3,rad=0.0",
        ),
    )
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y + 2, label, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=COLORS["bg"], edgecolor="none"))


# ──────────────────────────────────────────────────────────────
# Diagram 1: High-Level Architecture
# ──────────────────────────────────────────────────────────────
def draw_high_level_architecture():
    fig, ax = _setup_figure(16, 10, "LoadTest Framework - High-Level Architecture")

    # User layer
    _draw_box(ax, 5, 85, 18, 8, "GUI (PyQt5)", COLORS["primary"], "gui.py")
    _draw_box(ax, 28, 85, 18, 8, "CLI Mode", COLORS["primary"], "loadtest <config>")

    # Orchestrator
    _draw_box(ax, 15, 68, 25, 10, "Orchestrator", COLORS["secondary"], "orchestrate.py")

    # Docker Swarm layer
    _draw_box(ax, 2, 30, 96, 30, "", COLORS["card"])
    ax.text(50, 57, "Docker Swarm  (loadtest-network)", ha="center", va="center",
            color=COLORS["docker_blue"], fontsize=12, fontweight="bold")

    # Workers
    _draw_box(ax, 5, 40, 20, 12, "Worker 1", COLORS["secondary_light"], "speed_test")
    _draw_box(ax, 28, 40, 20, 12, "Worker 2", COLORS["secondary_light"], "web_browsing")
    _draw_box(ax, 51, 40, 20, 12, "Worker 3", COLORS["secondary_light"], "streaming")
    _draw_box(ax, 74, 40, 20, 12, "Worker 4", COLORS["secondary_light"], "voip_sipp")

    # Database
    _draw_box(ax, 60, 68, 25, 10, "PostgreSQL 16", COLORS["postgres"], "db-container:5432")

    # External targets
    _draw_box(ax, 5, 10, 20, 10, "iperf3 Server", COLORS["card"], "host:port")
    _draw_box(ax, 28, 10, 20, 10, "Web Servers", COLORS["card"], "HTTP/HTTPS")
    _draw_box(ax, 51, 10, 20, 10, "Jellyfin Server", COLORS["card"], "HTTP:8096")
    _draw_box(ax, 74, 10, 20, 10, "SIP Server (UAS)", COLORS["card"], "SIP:5060-5062")

    # Results
    _draw_box(ax, 15, 3, 25, 5, "CSV Results", COLORS["success"], "report_path/")

    # Arrows - User to Orchestrator
    _draw_arrow(ax, 14, 85, 20, 78, "config")
    _draw_arrow(ax, 37, 85, 32, 78, "config")

    # Orchestrator to Docker
    _draw_arrow(ax, 22, 68, 15, 52, "deploy")
    _draw_arrow(ax, 27, 68, 38, 52, "deploy")
    _draw_arrow(ax, 32, 68, 61, 52, "deploy")
    _draw_arrow(ax, 37, 68, 84, 52, "deploy")

    # Workers to DB
    _draw_arrow(ax, 25, 48, 60, 72, color=COLORS["postgres"])
    _draw_arrow(ax, 48, 48, 60, 72, color=COLORS["postgres"])
    _draw_arrow(ax, 71, 48, 75, 68, color=COLORS["postgres"])
    _draw_arrow(ax, 94, 48, 82, 68, color=COLORS["postgres"])

    # Workers to targets
    _draw_arrow(ax, 15, 40, 15, 20)
    _draw_arrow(ax, 38, 40, 38, 20)
    _draw_arrow(ax, 61, 40, 61, 20)
    _draw_arrow(ax, 84, 40, 84, 20)

    # Orchestrator to DB (export)
    _draw_arrow(ax, 40, 73, 60, 73, "export CSV", COLORS["success"])

    # DB to Results
    _draw_arrow(ax, 60, 68, 30, 8, color=COLORS["success"])

    output_path = os.path.join(OUTPUT_DIR, "architecture_high_level.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Diagram 2: Execution Pipeline
# ──────────────────────────────────────────────────────────────
def draw_execution_pipeline():
    fig, ax = _setup_figure(14, 16, "LoadTest Framework - Execution Pipeline")

    steps = [
        ("1. Validate Config", COLORS["primary"], "ConfigValidator"),
        ("2. Setup Report Path", COLORS["secondary"], "mkdir -p report_path"),
        ("3. Init Docker Infra", COLORS["docker_blue"], "Swarm + Network + PostgreSQL"),
        ("4. Deploy Worker Services", COLORS["secondary_light"], "docker service create (per scenario)"),
        ("5. Worker: Schedule Tests", COLORS["python"], "APScheduler (once / recurring)"),
        ("6. Worker: Execute Test", COLORS["primary_light"], "Protocol handler → metrics"),
        ("7. Worker: Write Metrics", COLORS["postgres"], "INSERT raw_metrics + results_log"),
        ("8. Worker: Finalize", COLORS["success"], "Scenario-scope eval + summary"),
        ("9. Orchestrator: Monitor", COLORS["secondary"], "Poll service status (10s)"),
        ("10. Cleanup & Export", COLORS["success"], "Remove services → CSV export"),
    ]

    box_h = 6
    gap = 3
    start_y = 90

    for i, (label, color, sublabel) in enumerate(steps):
        y = start_y - i * (box_h + gap)
        _draw_box(ax, 10, y, 80, box_h, label, color, sublabel, fontsize=11)
        if i < len(steps) - 1:
            _draw_arrow(ax, 50, y, 50, y - gap, color=COLORS["connector"])

    output_path = os.path.join(OUTPUT_DIR, "execution_pipeline.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Diagram 3: Database Schema (ER Diagram)
# ──────────────────────────────────────────────────────────────
def draw_database_schema():
    fig, ax = _setup_figure(16, 10, "LoadTest Framework - Database Schema (load_test)")

    # Scenarios table
    _draw_box(ax, 2, 60, 22, 25, "scenarios", COLORS["postgres"])
    fields = ["scenario_id  UUID PK", "protocol  VARCHAR", "config_snapshot  JSONB"]
    for i, f in enumerate(fields):
        ax.text(13, 80 - i * 4, f, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8, family="monospace")

    # test_runs table
    _draw_box(ax, 28, 60, 22, 25, "test_runs", COLORS["postgres"])
    fields = ["run_id  UUID PK", "scenario_id  UUID FK", "start_time  TIMESTAMP", "worker_node  VARCHAR"]
    for i, f in enumerate(fields):
        ax.text(39, 80 - i * 4, f, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8, family="monospace")

    # raw_metrics table
    _draw_box(ax, 54, 60, 22, 25, "raw_metrics", COLORS["postgres"])
    fields = ["id  UUID PK", "run_id  UUID FK", "metric_name  VARCHAR", "metric_value  VARCHAR", "timestamp  TIMESTAMP"]
    for i, f in enumerate(fields):
        ax.text(65, 80 - i * 4, f, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8, family="monospace")

    # results_log table
    _draw_box(ax, 54, 20, 22, 30, "results_log", COLORS["primary"])
    fields = ["id  UUID PK", "run_id  UUID FK", "metric_name  VARCHAR", "expected_value  VARCHAR",
              "measured_value  VARCHAR", "status  VARCHAR", "scope  VARCHAR"]
    for i, f in enumerate(fields):
        ax.text(65, 45 - i * 4, f, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8, family="monospace")

    # scenario_summary table
    _draw_box(ax, 2, 15, 28, 35, "scenario_summary", COLORS["success"])
    fields = ["id  UUID PK", "scenario_id  UUID FK", "metric_name  VARCHAR",
              "sample_count  INT", "avg_value  NUMERIC", "min_value  NUMERIC",
              "max_value  NUMERIC", "percentile  INT", "percentile_result  NUMERIC",
              "stddev_value  NUMERIC", "aggregated_at  TIMESTAMP"]
    for i, f in enumerate(fields):
        ax.text(16, 45 - i * 3, f, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=7, family="monospace")

    # Relationships
    _draw_arrow(ax, 24, 72, 28, 72, "1:N", COLORS["connector"])
    _draw_arrow(ax, 50, 72, 54, 72, "1:N", COLORS["connector"])
    _draw_arrow(ax, 50, 68, 54, 40, "1:N", COLORS["connector"])
    _draw_arrow(ax, 13, 60, 13, 50, "1:N", COLORS["connector"])

    output_path = os.path.join(OUTPUT_DIR, "database_schema.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Diagram 4: Worker Internal Architecture
# ──────────────────────────────────────────────────────────────
def draw_worker_architecture():
    fig, ax = _setup_figure(14, 12, "LoadTest Framework - Worker Container Architecture")

    # Container boundary
    _draw_box(ax, 3, 5, 94, 85, "", COLORS["card"])
    ax.text(50, 88, "Docker Container (loadtest:latest)", ha="center", va="center",
            color=COLORS["docker_blue"], fontsize=12, fontweight="bold")

    # Worker module
    _draw_box(ax, 8, 72, 30, 10, "worker.py", COLORS["secondary"], "Entry point")

    # Scheduler
    _draw_box(ax, 8, 52, 30, 12, "ScenarioScheduler", COLORS["python"],
              "APScheduler + ThreadPool(3)")

    # Test modules
    _draw_box(ax, 55, 72, 38, 10, "Test Modules", COLORS["primary"])
    modules = [
        ("speed_test.py", "iperf3 + ping"),
        ("web_browsing.py", "Playwright"),
        ("streaming.py", "Jellyfin + Playwright"),
        ("voip_sipp.py", "SIPp + tshark"),
    ]
    for i, (name, tool) in enumerate(modules):
        y = 65 - i * 7
        _draw_box(ax, 58, y, 32, 5, name, COLORS["primary_light"], tool, fontsize=8)

    # Utils
    _draw_box(ax, 8, 20, 30, 24, "Utilities", COLORS["card"])
    utils = ["db.py (connection pool)", "aggregator.py (stats)", "unit_converter.py",
             "error_logger.py", "config_validator.py"]
    for i, u in enumerate(utils):
        ax.text(23, 40 - i * 4, u, ha="center", va="center",
                color=COLORS["text_muted"], fontsize=8)

    # External connections
    _draw_box(ax, 55, 10, 18, 8, "PostgreSQL", COLORS["postgres"], "port 5432")
    _draw_box(ax, 76, 10, 18, 8, "Test Targets", COLORS["card"], "network")

    # Arrows
    _draw_arrow(ax, 23, 72, 23, 64, "schedule", COLORS["connector"])
    _draw_arrow(ax, 38, 58, 55, 72, "execute", COLORS["primary"])
    _draw_arrow(ax, 23, 52, 23, 44, "write", COLORS["connector"])
    _draw_arrow(ax, 38, 32, 55, 14, "INSERT", COLORS["postgres"])
    _draw_arrow(ax, 74, 42, 85, 18, "test traffic", COLORS["connector"])

    output_path = os.path.join(OUTPUT_DIR, "worker_architecture.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Diagram 5: Metric Evaluation Flow
# ──────────────────────────────────────────────────────────────
def draw_metric_evaluation_flow():
    fig, ax = _setup_figure(14, 12, "LoadTest Framework - Metric Evaluation Flow")

    # Test execution
    _draw_box(ax, 30, 88, 40, 6, "Test Module Returns Results", COLORS["primary"])

    # Extract metrics
    _draw_box(ax, 30, 76, 40, 6, "Extract Numeric Metrics", COLORS["secondary"],
              "Filter to configured expectations only")

    # Write raw
    _draw_box(ax, 30, 64, 40, 6, "INSERT raw_metrics", COLORS["postgres"])

    # Branch
    ax.text(50, 58, "Evaluation Scope?", ha="center", va="center",
            color=COLORS["warning"], fontsize=11, fontweight="bold")

    # Per-iteration
    _draw_box(ax, 5, 42, 40, 10, "per_iteration", COLORS["primary_light"],
              "Evaluate each result individually")

    # Scenario
    _draw_box(ax, 55, 42, 40, 10, "scenario (at finalization)", COLORS["secondary_light"],
              "Aggregate across all runs")

    # Unit conversion
    _draw_box(ax, 5, 28, 40, 8, "Unit Normalization", COLORS["card"],
              "native_unit → standard → compare")

    _draw_box(ax, 55, 28, 40, 8, "Aggregation", COLORS["card"],
              "avg / min / max / p1-p99 / stddev")

    # Compare
    _draw_box(ax, 5, 16, 40, 6, "Compare: measured OP expected", COLORS["card"])
    _draw_box(ax, 55, 16, 40, 6, "Compare: aggregated OP expected", COLORS["card"])

    # Results
    _draw_box(ax, 15, 5, 30, 6, "PASS", COLORS["success"])
    _draw_box(ax, 55, 5, 15, 6, "FAIL", COLORS["primary"])
    _draw_box(ax, 75, 5, 15, 6, "ERROR", COLORS["warning"])

    # Arrows
    _draw_arrow(ax, 50, 88, 50, 82)
    _draw_arrow(ax, 50, 76, 50, 70)
    _draw_arrow(ax, 50, 64, 50, 60)
    _draw_arrow(ax, 35, 56, 25, 52)
    _draw_arrow(ax, 65, 56, 75, 52)
    _draw_arrow(ax, 25, 42, 25, 36)
    _draw_arrow(ax, 75, 42, 75, 36)
    _draw_arrow(ax, 25, 28, 25, 22)
    _draw_arrow(ax, 75, 28, 75, 22)
    _draw_arrow(ax, 25, 16, 30, 11)
    _draw_arrow(ax, 75, 16, 62, 11)
    _draw_arrow(ax, 75, 16, 82, 11)

    output_path = os.path.join(OUTPUT_DIR, "metric_evaluation_flow.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Diagram 6: Network Topology
# ──────────────────────────────────────────────────────────────
def draw_network_topology():
    fig, ax = _setup_figure(16, 10, "LoadTest Framework - Docker Network Topology")

    # Host machine
    _draw_box(ax, 2, 2, 96, 90, "", COLORS["card"])
    ax.text(50, 90, "Host Machine (Ubuntu)", ha="center", va="center",
            color=COLORS["text"], fontsize=12, fontweight="bold")

    # Swarm overlay
    _draw_box(ax, 5, 20, 90, 55, "", COLORS["secondary"])
    ax.text(50, 72, "loadtest-network  (Docker Overlay, Attachable)", ha="center", va="center",
            color=COLORS["docker_blue"], fontsize=11, fontweight="bold")

    # Orchestrator (host-side)
    _draw_box(ax, 10, 80, 25, 8, "Orchestrator", COLORS["primary"], "Host process")

    # PostgreSQL
    _draw_box(ax, 10, 55, 22, 10, "db-container", COLORS["postgres"], "PostgreSQL 16\nport 5432")

    # Workers
    _draw_box(ax, 10, 35, 18, 12, "Worker 1", COLORS["secondary_light"],
              "speed_test")
    _draw_box(ax, 32, 35, 18, 12, "Worker 2", COLORS["secondary_light"],
              "web_browsing")
    _draw_box(ax, 54, 35, 18, 12, "Worker 3", COLORS["secondary_light"],
              "streaming")
    _draw_box(ax, 76, 35, 18, 12, "Worker 4", COLORS["secondary_light"],
              "voip_sipp")

    # Docker volume
    _draw_box(ax, 36, 55, 18, 10, "Docker Volume", COLORS["card"],
              "load-test")

    # CSV output
    _draw_box(ax, 60, 80, 25, 8, "CSV Results", COLORS["success"], "report_path/")

    # External
    _draw_box(ax, 10, 22, 82, 7, "External Test Targets (iperf3, HTTP, Jellyfin, SIP)", COLORS["card"])

    # Arrows
    _draw_arrow(ax, 22, 80, 22, 65, "manage", COLORS["connector"])
    _draw_arrow(ax, 35, 80, 60, 84, "export", COLORS["success"])
    _draw_arrow(ax, 19, 47, 19, 55, "SQL", COLORS["postgres"])
    _draw_arrow(ax, 41, 47, 25, 55, "SQL", COLORS["postgres"])
    _draw_arrow(ax, 63, 47, 28, 55, "SQL", COLORS["postgres"])
    _draw_arrow(ax, 85, 47, 32, 55, "SQL", COLORS["postgres"])
    _draw_arrow(ax, 32, 60, 36, 60, color=COLORS["connector"])
    _draw_arrow(ax, 19, 35, 19, 29)
    _draw_arrow(ax, 41, 35, 41, 29)
    _draw_arrow(ax, 63, 35, 63, 29)
    _draw_arrow(ax, 85, 35, 85, 29)

    output_path = os.path.join(OUTPUT_DIR, "network_topology.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"Generated: {output_path}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating LoadTest Framework diagrams...\n")
    draw_high_level_architecture()
    draw_execution_pipeline()
    draw_database_schema()
    draw_worker_architecture()
    draw_metric_evaluation_flow()
    draw_network_topology()
    print(f"\nAll diagrams saved to: {OUTPUT_DIR}/")

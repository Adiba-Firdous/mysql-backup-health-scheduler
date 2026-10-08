"""Simple daily scheduler using only the Python standard library."""

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta

from config_loader import load_config


def next_run_time(schedule_time: str) -> datetime:
    hour, minute = map(int, schedule_time.split(":"))
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def run_once(config_path: str) -> int:
    return subprocess.call(
        [sys.executable, "app.py", "--config", config_path],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the backup application daily.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--once", action="store_true", help="Run immediately once")
    args = parser.parse_args()

    config = load_config(args.config)
    schedule_time = config.get("schedule", {}).get("daily_time", "02:00")

    if args.once:
        return run_once(args.config)

    print(f"Daily scheduler started. Configured time: {schedule_time}")
    print("Press Ctrl+C to stop.")

    while True:
        target = next_run_time(schedule_time)
        seconds = max(1, int((target - datetime.now()).total_seconds()))
        print(f"Next run: {target.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(seconds)
        run_once(args.config)


if __name__ == "__main__":
    raise SystemExit(main())

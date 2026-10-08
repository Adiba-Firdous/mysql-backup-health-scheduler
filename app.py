"""Main application: backup MySQL, check health, and send alerts."""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from backup import create_backup
from email_alert import send_alert
from health import collect_health_metrics, evaluate_health
from config_loader import load_config


def configure_logging(log_file: str | None = None) -> None:
    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )


def write_report(report_dir: str, results: dict) -> Path:
    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"run_report_{timestamp}.txt"

    lines = [
        "MySQL Backup Health Scheduler Report",
        "=" * 40,
        f"Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"Backup: {'PASS' if results['backup_ok'] else 'FAIL'}",
        f"Health: {'PASS' if results['health_ok'] else 'FAIL'}",
    ]

    if results.get("backup_file"):
        lines.append(f"Backup file: {results['backup_file']}")

    metrics = results.get("metrics", {})
    if metrics:
        lines.append("\nHealth metrics:")
        for key, value in metrics.items():
            lines.append(f"  {key}: {value}")

    failures = results.get("health_failures", [])
    if failures:
        lines.append("\nHealth threshold alerts:")
        lines.extend(f"  - {item}" for item in failures)

    if results.get("error"):
        lines.append(f"\nError: {results['error']}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Schedule-friendly MySQL backup and health monitoring application."
    )
    parser.add_argument("--config", default="config.yaml", help="YAML configuration file")
    parser.add_argument("--skip-backup", action="store_true", help="Only run health monitoring")
    parser.add_argument("--skip-email", action="store_true", help="Do not send email alerts")
    args = parser.parse_args()

    config = load_config(args.config)
    logging_cfg = config.get("logging", {})
    configure_logging(logging_cfg.get("log_file"))

    logging.info("Starting MySQL backup and health check")

    results = {
        "backup_ok": False,
        "health_ok": False,
        "backup_file": None,
        "metrics": {},
        "health_failures": [],
        "error": None,
    }

    if not args.skip_backup:
        try:
            results["backup_file"] = str(create_backup(config))
            results["backup_ok"] = True
            logging.info("Backup completed successfully: %s", results["backup_file"])
        except Exception as exc:
            results["error"] = f"Backup failed: {exc}"
            logging.exception("Backup failed")
    else:
        results["backup_ok"] = True
        logging.info("Backup skipped")

    try:
        metrics = collect_health_metrics(config)
        health_ok, failures = evaluate_health(config, metrics)
        results["metrics"] = metrics
        results["health_ok"] = health_ok

        if failures:
            results["health_failures"] = failures
            logging.warning("Health threshold alerts detected")
            for failure in failures:
                logging.warning(failure)
        else:
            logging.info("All health metrics are within configured thresholds")
    except Exception as exc:
        results["error"] = f"Health check failed: {exc}"
        logging.exception("Health check failed")

    report = write_report(config.get("logging", {}).get("report_dir", "reports"), results)
    logging.info("Report written to %s", report)

    should_alert = not results["backup_ok"] or not results["health_ok"]
    if should_alert and not args.skip_email:
        subject = "MySQL Backup/Health Alert"
        body = report.read_text(encoding="utf-8")
        try:
            send_alert(config, subject, body)
            logging.info("Alert email sent")
        except Exception:
            logging.exception("Unable to send alert email")

    return 0 if results["backup_ok"] and results["health_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

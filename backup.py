"""MySQL backup module using mysqldump through subprocess."""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
import shutil


def _find_executable(config: dict) -> str:
    configured = config.get("mysql", {}).get("mysqldump_path", "")
    if configured and Path(configured).exists():
        return configured

    found = shutil.which("mysqldump")
    if found:
        return found

    raise FileNotFoundError(
        "mysqldump was not found. Set mysql.mysqldump_path in config.yaml "
        "or add MySQL's bin directory to PATH."
    )


def create_backup(config: dict) -> Path:
    mysql = config["mysql"]
    backup_cfg = config["backup"]

    database = mysql["database"]
    output_dir = Path(backup_cfg.get("directory", "backups"))
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{database}_{timestamp}.sql"

    command = [
        _find_executable(config),
        "--host", str(mysql.get("host", "localhost")),
        "--port", str(mysql.get("port", 3306)),
        "--user", str(mysql["user"]),
        "--result-file", str(output_file),
        database,
    ]

    env = os.environ.copy()
    password = mysql.get("password", "")
    if password:
        env["MYSQL_PWD"] = password

    timeout = int(backup_cfg.get("timeout_seconds", 300))
    logging.info("Creating MySQL backup for database '%s'", database)

    try:
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    finally:
        # Avoid retaining the password in our process environment after the call.
        env.pop("MYSQL_PWD", None)

    if result.returncode != 0:
        if output_file.exists():
            output_file.unlink()
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"mysqldump exited with code {result.returncode}: {detail}")

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise RuntimeError("mysqldump completed but produced an empty backup file")

    logging.info("Backup size: %d bytes", output_file.stat().st_size)

    retention_days = int(backup_cfg.get("retention_days", 7))
    _apply_retention(output_dir, database, retention_days)

    return output_file


def _apply_retention(directory: Path, database: str, retention_days: int) -> None:
    if retention_days <= 0:
        return

    cutoff = datetime.now().timestamp() - retention_days * 86400
    pattern = f"{database}_*.sql"

    for path in directory.glob(pattern):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            logging.info("Removed old backup: %s", path)

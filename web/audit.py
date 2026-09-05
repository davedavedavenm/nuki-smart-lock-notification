"""Append-only audit trail for admin and security-relevant actions.

Entries are JSON lines in data/audit.jsonl. The file is rotated in-place
when it grows past MAX_BYTES: the most recent half is kept.
"""
import os
import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger('nuki_web')

MAX_BYTES = 5 * 1024 * 1024  # rotate at 5 MB


class AuditLog:
    def __init__(self, data_dir, filename="audit.jsonl"):
        self.path = os.path.join(data_dir, filename)
        self._lock = threading.Lock()

    def record(self, action, actor="anonymous", detail="", status="success", ip=None):
        """Append one audit entry. Never raises — auditing must not break requests."""
        entry = {
            "ts": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "actor": actor,
            "ip": ip or "",
            "action": action,
            "detail": detail,
            "status": status,
        }
        try:
            with self._lock:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, 'a') as f:
                    f.write(json.dumps(entry) + "\n")
                self._rotate_if_needed()
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")

    def _rotate_if_needed(self):
        try:
            if os.path.getsize(self.path) <= MAX_BYTES:
                return
            with open(self.path, 'r') as f:
                lines = f.readlines()
            keep = lines[len(lines) // 2:]
            with open(self.path, 'w') as f:
                f.writelines(keep)
            logger.info(f"Audit log rotated, kept {len(keep)} entries")
        except Exception as e:
            logger.error(f"Audit log rotation failed: {e}")

    def recent(self, limit=200, action_filter=None, status_filter=None):
        """Return the most recent entries, newest first."""
        entries = []
        try:
            if not os.path.exists(self.path):
                return entries
            with open(self.path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if action_filter and action_filter not in entry.get("action", ""):
                        continue
                    if status_filter and entry.get("status") != status_filter:
                        continue
                    entries.append(entry)
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
        entries.reverse()
        return entries[:limit]

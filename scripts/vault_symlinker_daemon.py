#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Sovereign Vault Daemon (Clio Metal) - PRODUCTION HARDENED
Path: /home/james/stacklabs/scripts/vault_symlinker_daemon.py
Audited by Qwen 2.5 72B Crucible: Enforces atomic os.replace, atomic symlink swaps,
dead-letter quarantine, and bounded inode deduplication.
"""
import os
import re
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/home/james/stacklabs/logs/vault_symlinker.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Resolve canonical physical root
REPO_VAULT = Path("/home/james/stacklabs/vault")
VAULT_ROOT = Path("/vault") if Path("/vault").exists() else REPO_VAULT
RAW_DROPS = VAULT_ROOT / "raw_drops"
BY_PERSON = VAULT_ROOT / "by_person"
BY_DATE = VAULT_ROOT / "by_date"
BY_TOPIC = VAULT_ROOT / "by_topic"
QUARANTINE = VAULT_ROOT / "quarantine"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def clean_slug(val: str, default: str = "unassigned") -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', str(val).strip().lower()).strip('_')
    return cleaned if cleaned else default

def parse_frontmatter(content: str) -> dict:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip().strip("\"'")
    return meta

class RawDropHandler(FileSystemEventHandler):
    def __init__(self):
        self.processed_inodes = set()

    def on_closed(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self._queue_process(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(".md"):
            self._queue_process(Path(event.dest_path))

    def _queue_process(self, file_path: Path):
        if not file_path.exists() or not file_path.is_file():
            return
        
        try:
            inode = file_path.stat().st_ino
            if inode in self.processed_inodes:
                return
            
            # Bound cache to prevent memory drift
            if len(self.processed_inodes) > 2048:
                self.processed_inodes.clear()
            self.processed_inodes.add(inode)
            
            self._process_file_atomic(file_path, inode)
        except Exception as e:
            logger.error(f"Failed to queue {file_path}: {e}")

    def _atomic_symlink(self, target: Path, link_path: Path, inode: int):
        """Atomically creates or updates a symlink via tempfile rename."""
        link_dir = link_path.parent
        link_dir.mkdir(parents=True, exist_ok=True)
        rel_to_target = os.path.relpath(target, link_dir)
        
        tmp_link = link_dir / f".tmp_{link_path.name}_{inode}"
        try:
            if tmp_link.is_symlink() or tmp_link.exists():
                tmp_link.unlink()
            tmp_link.symlink_to(rel_to_target)
            os.replace(tmp_link, link_path)
        except Exception as e:
            logger.error(f"Atomic symlink failed for {link_path} -> {rel_to_target}: {e}")
            if tmp_link.is_symlink() or tmp_link.exists():
                tmp_link.unlink()

    def _process_file_atomic(self, file_path: Path, inode: int):
        if not file_path.exists():
            return
        try:
            if file_path.stat().st_size == 0:
                return
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.warning(f"UTF-8 decode failed for {file_path}. Quarantining. ({e})")
            self._quarantine(file_path)
            return
        except Exception as e:
            logger.error(f"Unexpected read error for {file_path}: {e}")
            return

        meta = parse_frontmatter(content)
        if not meta or "person" not in meta:
            logger.info(f"No valid frontmatter 'person' in {file_path}. Quarantining.")
            self._quarantine(file_path)
            return

        person = clean_slug(meta.get("person", "unassigned"))
        date_str = clean_slug(meta.get("date", time.strftime("%Y-%m-%d")), default="undated")
        msg_type = clean_slug(meta.get("type", "notes"), default="notes")
        
        topics_raw = meta.get("topic", meta.get("topics", "general"))
        topics = [clean_slug(t, default="general") for t in str(topics_raw).split(",") if t.strip()]

        # 1. Physical Inode Placement (STRICT POSIX ATOMICITY)
        person_dir = BY_PERSON / person / msg_type
        person_dir.mkdir(parents=True, exist_ok=True)
        canonical_target = person_dir / file_path.name

        try:
            os.replace(str(file_path), str(canonical_target))
        except OSError as e:
            if e.errno == 18: # EXDEV
                logger.critical(f"EXDEV: Cross-device link attempted. Ensure raw_drops and by_person are on the same mount. ({file_path} -> {canonical_target})")
            else:
                logger.error(f"Atomic move failed for {file_path}: {e}")
            self.processed_inodes.discard(inode)
            return

        # 2. Date Projection Symlink (100% Atomic Swap)
        date_dir = BY_DATE / date_str
        date_link = date_dir / f"{person}_{canonical_target.name}"
        self._atomic_symlink(canonical_target, date_link, inode)

        # 3. Topic Projection Symlinks (100% Atomic Swap)
        for topic in topics:
            topic_dir = BY_TOPIC / topic
            topic_link = topic_dir / f"{person}_{canonical_target.name}"
            self._atomic_symlink(canonical_target, topic_link, inode)

        logger.info(f"Successfully processed and linked: {canonical_target.name} (person={person}, date={date_str}, topics={topics})")

    def _quarantine(self, file_path: Path):
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(str(file_path), str(QUARANTINE / file_path.name))
        except Exception as e:
            logger.error(f"Failed to quarantine {file_path}: {e}")

if __name__ == "__main__":
    # Ensure log directory exists
    Path("/home/james/stacklabs/logs").mkdir(parents=True, exist_ok=True)
    
    for p in [RAW_DROPS, BY_PERSON, BY_DATE, BY_TOPIC, QUARANTINE]:
        p.mkdir(parents=True, exist_ok=True)

    handler = RawDropHandler()
    observer = Observer()
    observer.schedule(handler, str(RAW_DROPS), recursive=False)
    observer.start()
    logger.info("Vault Symlinker Daemon started. Watching %s", RAW_DROPS)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down daemon...")
        observer.stop()
    observer.join()

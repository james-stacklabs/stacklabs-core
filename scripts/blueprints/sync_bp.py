"""sync blueprint extracted from dead_drop_server.py (generated). Routes unchanged."""
from flask import Blueprint
from scripts.dead_drop_common import *  # noqa: F401,F403

bp = Blueprint("sync", __name__)


SYNC_DROPZONE_DIR = Path("/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions")


SYNC_DROPZONE_DIR.mkdir(parents=True, exist_ok=True)


NOTEBOOK_SYNC_BASE_DIR = Path("/home/james/sovereign_inbox/notebook_sync")


def discover_notebook_envelopes() -> Dict[str, Dict[str, Any]]:
    """
    Dynamically scans /home/james/sovereign_inbox/notebook_sync for all subdirectories.
    Automatically generates key, name, id, icon, remote, path, description, hue.
    Guarantees: Dropping ANY new directory into notebook_sync/ instantly surfaces in UI with ZERO code changes.
    """
    envelopes: Dict[str, Dict[str, Any]] = {}
    if not NOTEBOOK_SYNC_BASE_DIR.exists():
        return envelopes

    subdirs: List[Path] = [
        d for d in NOTEBOOK_SYNC_BASE_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]

    weekly_path = NOTEBOOK_SYNC_BASE_DIR / "StackLabs_Internal" / "weekly_additions"
    if weekly_path.is_dir() and not any(d.name == "weekly_additions" for d in subdirs):
        subdirs.append(weekly_path)

    preferred_order = [
        "07_JohnnyCarroll_Prospectus",
        "03_WildSeed_Sovereign_Swarm",
        "06_Davidson_Malone_Prospectus",
        "04_ArkleVet_Prospectus",
        "05_SanJuan_Prospectus",
        "02_Edge_Platform_Engineering",
        "StackLabs_Internal",
        "weekly_additions",
        "15_Horizon_Internal",
        "16_Emergent_Society"
    ]

    def sort_key(d: Path):
        k = d.name
        if k in preferred_order:
            return (0, preferred_order.index(k), k)
        m = re.match(r'^(\d+)', k)
        if m:
            return (1, int(m.group(1)), k)
        return (2, 0, k.lower())

    subdirs.sort(key=sort_key)

    known_labels = {
        "07_JohnnyCarroll_Prospectus": "07 Johnny Carroll",
        "03_WildSeed_Sovereign_Swarm": "03 WildSeed Swarm",
        "06_Davidson_Malone_Prospectus": "06 Davidson Malone",
        "04_ArkleVet_Prospectus": "04 Arkle Vet",
        "05_SanJuan_Prospectus": "05 San Juan",
        "05_SanJuanIslands_Authority": "05 San Juan Islands",
        "02_Edge_Platform_Engineering": "02 Edge Platform",
        "15_Horizon_Internal": "15 Horizon Internal",
        "16_Emergent_Society": "16 Emergent Society",
        "StackLabs_Internal": "StackLabs Internal",
        "weekly_additions": "weekly_additions"
    }

    known_descriptions = {
        "07_JohnnyCarroll_Prospectus": "Glendale Custom Cabinetry & Millwork Prospectus",
        "03_WildSeed_Sovereign_Swarm": "WildSeed Extracts Living Soil & Solventless Terpene Swarm (29 Sources)",
        "06_Davidson_Malone_Prospectus": "Davidson Homes / Jeremy Malone Builder Moat",
        "04_ArkleVet_Prospectus": "Arkle Veterinary Care Search Authority",
        "05_SanJuan_Prospectus": "Better Properties San Juan Islands Authority",
        "02_Edge_Platform_Engineering": "Model-S Physical Constants, TCO Economics & Fleet Architecture",
        "15_Horizon_Internal": "Horizon Predictive Forensics & Primary Source Inspector",
        "16_Emergent_Society": "The SICKO Exchange // Autonomous Dive Bar Simulation & Hemodynamic Engine",
        "StackLabs_Internal": "Master Engineering Chronicles & Daily Deliverables",
        "weekly_additions": "Standalone Non-Consolidatable Weekly Assets"
    }

    for d in subdirs:
        key = d.name
        kl = key.lower()

        # Clean formatted label
        if key in known_labels:
            name = known_labels[key]
        else:
            s = key.replace('_', ' ').strip()
            for suff in [' Prospectus', ' Engineering', ' Authority', ' Swarm']:
                if s.endswith(suff):
                    s = s[:-len(suff)].strip()
            name = s or key

        # Smart contextual icon
        if any(w in kl for w in ['wildseed', 'weed']):
            icon = '🌿'
        elif any(w in kl for w in ['carroll', 'wood', 'cabinet', 'millwork']):
            icon = '🪚'
        elif any(w in kl for w in ['davidson', 'malone', 'builder']):
            icon = '🏗️'
        elif any(w in kl for w in ['arkle', 'vet', 'dog', 'puppy', 'feline', 'canine']) or re.search(r'\bcat\b', kl):
            icon = '🐾'
        elif any(w in kl for w in ['sanjuan', 'island']):
            icon = '🌲'
        elif any(w in kl for w in ['edge', 'model']):
            icon = '⚡'
        elif any(w in kl for w in ['internal', 'stacklabs']):
            icon = '🛡️'
        elif any(w in kl for w in ['weekly', 'addition']):
            icon = '📦'
        elif any(w in kl for w in ['society', 'emergent']):
            icon = '🏛️'
        else:
            icon = '📁'

        # Remote target mapping
        if key == "StackLabs_Internal":
            remote = "stacklabs_edge:StackLabs_Internal"
        elif 'weekly' in kl or 'addition' in kl:
            remote = "stacklabs_edge:weekly_additions"
        else:
            remote = f"stacklabs_edge:{key}"

        # Short ID
        m = re.match(r'^(\d+)', key)
        if m:
            envelope_id = m.group(1).zfill(2)
        elif 'internal' in kl:
            envelope_id = "INT"
        elif 'weekly' in kl or 'addition' in kl:
            envelope_id = "WK"
        else:
            parts = [w for w in re.split(r'[^a-zA-Z0-9]+', key) if w]
            if len(parts) >= 2:
                envelope_id = (parts[0][0] + parts[1][0]).upper()
            elif parts:
                envelope_id = parts[0][:3].upper()
            else:
                envelope_id = "DIR"

        # Theme Hue
        hue = 'gold' if envelope_id in ['07', '06', '02', 'INT'] else 'cyan'

        description = known_descriptions.get(key, f"Tactical Vector Dossier: {name}")

        envelopes[key] = {
            "key": key,
            "name": name,
            "id": envelope_id,
            "icon": icon,
            "path": d,
            "remote": remote,
            "description": description,
            "hue": hue
        }

    return envelopes


NOTEBOOK_ENVELOPES: Dict[str, Dict[str, Any]] = discover_notebook_envelopes()


CLEAN_ROOM_LANES: Dict[str, List[str]] = {
    "02_Edge_Platform_Engineering": [
        "07_SUBNET_STEWARD_ROLE_AND_HUMAN_EQUITY_GOVERNANCE.md",
        "ARCHITECTURE_SPEC_SOVEREIGN_INTELLIGENCE_RADAR_SIR.md",
        "Executive_Syndicate_Briefing_StackLabs_Model_S.md",
        "PHASE_0_ZERO_HOUR_PROVISIONING_AND_STAGING_RUNBOOK.md",
        "SKILL_NO_SNAKE_OIL_SPARK_GOVERNANCE.md",
        "SPEC_ANTHROPOMORPHIC_DOMAIN_MICROSERVICES_ADM_FRAMEWORK.md",
        "SPEC_SIR_MOD_002_PREDICTIVE_HORIZON_RADAR.md",
        "STACKLABS_SANITIZED_PLATFORM_CAPABILITIES_AND_POWER_TOOLS.md",
        "Sovereign_Power_Tools_and_Microservices_Catalog.md",
        "The Campsite Protocol_ Operational Invariants & Human Equity Governance.md"
    ],
    "03_WildSeed_Sovereign_Swarm": [
        "09_WILDSEED_TENANT_ZERO_AGREEMENT_AND_SOW.md",
        "COMPANION_SOURCE_WILDSEED_SERP_AND_SCHEMA_EVIDENCE.md",
        "PAWEL_CLAUDE_ADM_ROLEPLAY_SIMULATION.md",
        "StackLabs LLC & WildSeed LLC — Commercial Sweetener Addendum & Pilot SOW.md",
        "WHITE_PAPER_WILDSEED_ALGORITHMIC_RECLAMATION_AND_EAT_ENGINE.md",
        "WILDSEED_EXTRACTS_PRODUCT_DATA_SHEET.md",
        "WILDSEED_MODULE_01_SOLVENTLESS_EXTRACTION_THERMODYNAMICS.md",
        "WILDSEED_MODULE_02_LIVING_SOIL_TERPENE_BIOGENESIS_AND_CURING_CHEMISTRY.md"
    ]
}


REMOTE_TARGETS: Dict[str, List[str]] = {
    "TARGET_EDGE": [
        "stacklabs_edge:02_Edge_Platform_Engineering",
        "stacklabs_edge:03_WildSeed_Sovereign_Swarm"
    ],
    "TARGET_VAULT": [
        "stacklabs_vault:Corporate_Records/weekly_additions"
    ],
    "TARGET_DUAL": [
        "stacklabs_edge:02_Edge_Platform_Engineering",
        "stacklabs_edge:03_WildSeed_Sovereign_Swarm",
        "stacklabs_vault:Corporate_Records/weekly_additions"
    ],
    "TARGET_OS": [
        "stacklabs_edge:weekly_additions"
    ]
}


class SovereignSyncService:
    """
    Production-grade file synchronization engine.
    Encapsulates process isolation, network timeouts, and streaming log queues.
    Supports multi-envelope NotebookLM sync with clean mode and clutter pruning.
    """
    def __init__(self, dropzone_dir: Path, rclone_path: str = "/usr/bin/rclone"):
        self.dropzone_dir = dropzone_dir
        self.rclone_path = rclone_path
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def get_envelopes(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically discovers all notebook sync envelopes."""
        return discover_notebook_envelopes()

    def get_envelopes_summary(self) -> Dict[str, Any]:
        """Returns summary of all dynamically discovered notebook envelopes with counts and paths."""
        summary = []
        source_exts = {'.md', '.pdf', '.txt'}
        all_envelopes = self.get_envelopes()
        last_sync_time = "Unknown"
        for candidate_log in [
            Path("/home/james/SovereignOS/logs/sync_to_gdrive.log"),
            Path("/home/james/SovereignOS/logs/sync.log")
        ]:
            if candidate_log.exists():
                try:
                    dt = datetime.fromtimestamp(candidate_log.stat().st_mtime)
                    last_sync_time = dt.strftime("%b %d, %H:%M EDT")
                    break
                except OSError:
                    pass

        for key, env in all_envelopes.items():
            p: Path = env["path"]
            total_files = 0
            pristine_files = 0
            clutter_files = 0
            total_bytes = 0
            last_mtime = 0.0
            if p.exists():
                for item in p.iterdir():
                    if item.is_file() and not item.name.startswith('.'):
                        total_files += 1
                        ext = item.suffix.lower()
                        if ext in source_exts:
                            pristine_files += 1
                        else:
                            clutter_files += 1
                        try:
                            st = item.stat()
                            total_bytes += st.st_size
                            if st.st_mtime > last_mtime:
                                last_mtime = st.st_mtime
                        except OSError:
                            pass

            if last_mtime > 0:
                dt = datetime.fromtimestamp(last_mtime)
                last_mtime_human = dt.strftime("%b %d, %H:%M EDT")
                last_mtime_iso = dt.isoformat()
            else:
                last_mtime_human = "Never"
                last_mtime_iso = None

            summary.append({
                "key": key,
                "name": env["name"],
                "id": env.get("id", key[:2]),
                "icon": env["icon"],
                "hue": env.get("hue", "cyan"),
                "path": str(env["path"]),
                "remote": env["remote"],
                "description": env.get("description", ""),
                "total_files": total_files,
                "pristine_files": pristine_files,
                "clutter_files": clutter_files,
                "total_bytes": total_bytes,
                "total_size_human": self._format_size(total_bytes),
                "last_modified": last_mtime_human,
                "last_modified_iso": last_mtime_iso
            })
        return {
            "status": "success",
            "envelopes": summary,
            "last_sync_timestamp": last_sync_time
        }

    def get_staged_inventory(self, envelope_key: Optional[str] = None) -> Dict[str, Any]:
        """Scans the specified envelope (or default), returning files classified by pristine source status."""
        all_envelopes = self.get_envelopes()
        if not envelope_key or envelope_key not in all_envelopes:
            if "07_JohnnyCarroll_Prospectus" in all_envelopes:
                envelope_key = "07_JohnnyCarroll_Prospectus"
            elif all_envelopes:
                envelope_key = next(iter(all_envelopes.keys()))
            else:
                envelope_key = "07_JohnnyCarroll_Prospectus"

        env = all_envelopes.get(envelope_key)
        if not env:
            target_dir = NOTEBOOK_SYNC_BASE_DIR / envelope_key
            env = {
                "name": envelope_key,
                "icon": "📁",
                "path": target_dir,
                "remote": f"stacklabs_edge:{envelope_key}",
                "description": f"Vector Dossier: {envelope_key}"
            }
        else:
            target_dir = env["path"]

        files: List[Dict[str, Any]] = []
        total_bytes = 0
        now = time.time()
        pristine_count = 0
        clutter_count = 0
        source_exts = {'.md', '.pdf', '.txt'}

        if target_dir.exists():
            for item in target_dir.iterdir():
                if item.is_file() and not item.name.startswith('.'):
                    try:
                        stat = item.stat()
                        size = stat.st_size
                        mtime = stat.st_mtime
                        total_bytes += size
                        delta_sec = max(0, now - mtime)
                        ext = item.suffix.lower()

                        is_source = ext in source_exts
                        is_clutter = not is_source

                        if is_source:
                            pristine_count += 1
                        else:
                            clutter_count += 1

                        files.append({
                            "filename": item.name,
                            "size_bytes": size,
                            "size_human": self._format_size(size),
                            "mtime_epoch": mtime,
                            "mtime_relative": self._format_relative_time(delta_sec),
                            "extension": ext,
                            "is_notebooklm_source": is_source,
                            "is_clutter": is_clutter,
                            "is_whitelisted": is_source,
                            "preselected": is_source
                        })
                    except OSError as err:
                        logger.warning("Failed to inspect %s: %s", item.name, err)

        # Sort: pristine sources first, then newest first
        files.sort(key=lambda x: (not x["is_notebooklm_source"], -x["mtime_epoch"]))

        return {
            "status": "success",
            "envelope": envelope_key,
            "envelope_name": env["name"],
            "envelope_icon": env["icon"],
            "envelope_description": env.get("description", ""),
            "remote": env["remote"],
            "dropzone_path": str(target_dir),
            "total_files": len(files),
            "pristine_files": pristine_count,
            "clutter_files": clutter_count,
            "total_bytes": total_bytes,
            "total_size_human": self._format_size(total_bytes),
            "files": files
        }

    def prune_local_clutter(self, envelope_key: str) -> Dict[str, Any]:
        """Deletes local non-source clutter (.png, .html, etc.) and empty subdirectories in envelope folder."""
        all_envelopes = self.get_envelopes()
        if not envelope_key or envelope_key not in all_envelopes:
            target_dir = NOTEBOOK_SYNC_BASE_DIR / envelope_key
            if not target_dir.exists():
                raise ValueError(f"Invalid envelope key: {envelope_key}")
            env = {"path": target_dir}
        else:
            env = all_envelopes[envelope_key]
            target_dir = env["path"]

        if not target_dir.exists():
            return {"status": "success", "envelope": envelope_key, "deleted_files": [], "deleted_dirs": [], "count": 0}

        deleted_files = []
        deleted_dirs = []
        clutter_exts = {'.png', '.html', '.htm', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.json', '.log', '.tmp'}

        # 1. Prune clutter files
        for item in list(target_dir.iterdir()):
            if item.is_file() and not item.name.startswith('.'):
                if item.suffix.lower() in clutter_exts:
                    try:
                        fname = item.name
                        item.unlink()
                        deleted_files.append(fname)
                        logger.info("Pruned clutter file: %s from %s", fname, envelope_key)
                    except Exception as err:
                        logger.error("Failed to delete %s: %s", item, err)

        # 2. Prune empty subdirectories (bottom-up)
        for root, dirs, files in os.walk(str(target_dir), topdown=False):
            for d in dirs:
                dir_path = Path(root) / d
                try:
                    if not any(dir_path.iterdir()):
                        rel_dir = str(dir_path.relative_to(target_dir))
                        dir_path.rmdir()
                        deleted_dirs.append(rel_dir)
                        logger.info("Pruned empty directory: %s from %s", rel_dir, envelope_key)
                except Exception as err:
                    logger.warning("Could not remove dir %s: %s", dir_path, err)

        return {
            "status": "success",
            "envelope": envelope_key,
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "count": len(deleted_files)
        }

    def dispatch_sync(
        self,
        envelope_key: Optional[str] = None,
        target_key: Optional[str] = None,
        selected_files: Optional[List[str]] = None,
        clean_mode: bool = True,
        dry_run: bool = False
    ) -> str:
        """Launches an asynchronous sync job in an isolated worker thread."""
        task_id = f"sync-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        all_envelopes = self.get_envelopes()
        if envelope_key and envelope_key in all_envelopes:
            env = all_envelopes[envelope_key]
            remotes = [env["remote"]]
            source_dir = env["path"]
            mode = "ENVELOPE"
            envelope_name = env["name"]
        elif target_key and target_key in REMOTE_TARGETS:
            remotes = REMOTE_TARGETS[target_key]
            source_dir = self.dropzone_dir
            mode = "LEGACY_TARGET"
            envelope_name = target_key
        else:
            envelope_key = "07_JohnnyCarroll_Prospectus"
            env = all_envelopes.get(envelope_key, {
                "name": "07 Johnny Carroll",
                "icon": "🪚",
                "path": NOTEBOOK_SYNC_BASE_DIR / envelope_key,
                "remote": f"stacklabs_edge:{envelope_key}"
            })
            remotes = [env["remote"]]
            source_dir = env["path"]
            mode = "ENVELOPE"
            envelope_name = env["name"]

        task_record = {
            "task_id": task_id,
            "mode": mode,
            "envelope_key": envelope_key,
            "envelope_name": envelope_name,
            "source_dir": source_dir,
            "target_key": target_key,
            "remotes": remotes,
            "selected_files": selected_files or [],
            "clean_mode": clean_mode,
            "dry_run": dry_run,
            "status": "PENDING",
            "queue": queue.Queue(maxsize=1000),
            "process": None,
            "created_at": time.time(),
            "completed": False
        }

        with self.lock:
            self.active_tasks[task_id] = task_record

        worker = threading.Thread(
            target=self._run_sync_worker,
            args=(task_record,),
            daemon=True,
            name=f"SyncWorker-{task_id}"
        )
        worker.start()
        return task_id

    def abort_task(self, task_id: str) -> bool:
        """Terminates an ongoing sync subprocess via SIGTERM and SIGKILL."""
        with self.lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return False

            proc: Optional[subprocess.Popen] = task.get("process")
            if proc and proc.poll() is None:
                logger.info("Aborting sync process: %s", task_id)
                try:
                    proc.terminate()
                    threading.Timer(3.0, self._force_kill, args=(proc,)).start()
                    task["status"] = "ABORTED"
                    task["queue"].put({"event": "abort", "data": {"message": "Sync operation cancelled by operator."}})
                    return True
                except Exception as err:
                    logger.error("Error terminating process %s: %s", task_id, err)
                    return False
        return False

    def stream_telemetry(self, task_id: str) -> Generator[str, None, None]:
        """SSE generator yielding live log and progress events to frontend."""
        task = self.active_tasks.get(task_id)
        if not task:
            yield f"event: error\ndata: {json.dumps({'message': 'Task ID not found'})}\n\n"
            return

        msg_queue: queue.Queue = task["queue"]
        while True:
            try:
                msg = msg_queue.get(timeout=1.0)
                event_type = msg.get("event", "log")
                payload = json.dumps(msg.get("data", {}))
                yield f"event: {event_type}\ndata: {payload}\n\n"

                if event_type in ("complete", "abort", "error"):
                    break
            except queue.Empty:
                if task.get("completed", False) and msg_queue.empty():
                    break
                yield ": keepalive\n\n"

    def _execute_rclone_step(
        self,
        task: Dict[str, Any],
        remote: str,
        source_dir: Path,
        include_files: Optional[List[str]],
        clean_mode: bool,
        log_label: str
    ) -> bool:
        """Executes a single rclone sync or copy operation with SSE streaming."""
        dry_run = task["dry_run"]
        msg_queue = task["queue"]
        action = "sync" if clean_mode else "copy"

        cmd = [
            self.rclone_path, action,
            str(source_dir), remote,
            "--contimeout", "5s",
            "--timeout", "15s",
            "--low-level-retries", "2",
            "--retries", "2",
            "--drive-chunk-size", "64M",
            "--transfers", "4",
            "--checkers", "4",
            "--stats", "1s",
            "--stats-one-line",
            "-v"
        ]
        if dry_run:
            cmd.append("--dry-run")

        if clean_mode:
            cmd.extend([
                "--include", "*.md",
                "--include", "*.pdf",
                "--include", "*.txt",
                "--delete-excluded"
            ])
        elif include_files:
            for f in include_files:
                cmd.extend(["--include", f])

        msg_queue.put({
            "event": "log",
            "data": {"line": log_label}
        })

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            task["process"] = proc

            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    clean_line = line.strip()
                    if clean_line:
                        if "Transferred:" in clean_line:
                            msg_queue.put({
                                "event": "progress",
                                "data": {"raw": clean_line}
                            })
                        else:
                            msg_queue.put({
                                "event": "log",
                                "data": {"line": clean_line}
                            })

            proc.wait()
            if proc.returncode != 0 and task.get("status") != "ABORTED":
                msg_queue.put({
                    "event": "log",
                    "data": {"line": f"❌ ERROR: Remote {remote} exited with code {proc.returncode}"}
                })
                return False
            return True

        except Exception as err:
            logger.error("Sync worker exception on %s: %s", remote, err)
            msg_queue.put({
                "event": "log",
                "data": {"line": f"💥 CRITICAL FAULT on {remote}: {str(err)}"}
            })
            return False

    def _run_sync_worker(self, task: Dict[str, Any]) -> None:
        """Executes rclone for destination with real-time SSE streaming."""
        task_id = task["task_id"]
        mode = task.get("mode", "ENVELOPE")
        remotes: List[str] = task["remotes"]
        source_dir: Path = task.get("source_dir", self.dropzone_dir)
        files: List[str] = task.get("selected_files", [])
        clean_mode: bool = task.get("clean_mode", True)
        dry_run: bool = task.get("dry_run", False)
        msg_queue: queue.Queue = task["queue"]
        envelope_name: str = task.get("envelope_name", "Sync Task")

        task["status"] = "RUNNING"
        msg_queue.put({
            "event": "start",
            "data": {
                "task_id": task_id,
                "mode": mode,
                "envelope_name": envelope_name,
                "remotes": remotes,
                "clean_mode": clean_mode,
                "dry_run": dry_run,
                "file_count": len(files) if files else "ALL"
            }
        })

        overall_success = True
        t0 = time.time()

        if mode == "ENVELOPE":
            remote = remotes[0]
            mode_desc = "CLEAN SYNC (--delete-excluded pristine sources)" if clean_mode else "STANDARD COPY"
            log_label = f"⚡ Syncing Envelope [{envelope_name}] ➔ {remote} [{mode_desc}]"
            step_ok = self._execute_rclone_step(task, remote, source_dir, files, clean_mode, log_label)
            if not step_ok:
                overall_success = False

        elif task.get("target_key") == "TARGET_EDGE":
            # Multi-lane clean room routing
            for lane_name, lane_files in CLEAN_ROOM_LANES.items():
                if task.get("status") == "ABORTED":
                    break
                lane_sync_files = [f for f in lane_files if f in files] if files else list(lane_files)
                if not lane_sync_files:
                    msg_queue.put({
                        "event": "log",
                        "data": {"line": f"ℹ️ Skipping sovereign_os:StackLabs_Edge/{lane_name}/ (0 files selected)"}
                    })
                    continue

                remote = f"stacklabs_edge:{lane_name}"
                log_label = f"⚡ Transmitting {len(lane_sync_files)} files to {remote}/..."
                step_ok = self._execute_rclone_step(task, remote, source_dir, lane_sync_files, False, log_label)
                if not step_ok:
                    overall_success = False

        elif task.get("target_key") == "TARGET_DUAL":
            for lane_name, lane_files in CLEAN_ROOM_LANES.items():
                if task.get("status") == "ABORTED":
                    break
                lane_sync_files = [f for f in lane_files if f in files] if files else list(lane_files)
                if not lane_sync_files:
                    continue
                remote = f"stacklabs_edge:{lane_name}"
                log_label = f"⚡ Transmitting {len(lane_sync_files)} files to {remote}/..."
                step_ok = self._execute_rclone_step(task, remote, source_dir, lane_sync_files, False, log_label)
                if not step_ok:
                    overall_success = False

            if task.get("status") != "ABORTED":
                vault_remote = "stacklabs_vault:Corporate_Records/weekly_additions"
                log_label = f"⚡ Transmitting to {vault_remote}..."
                step_ok = self._execute_rclone_step(task, vault_remote, source_dir, files, False, log_label)
                if not step_ok:
                    overall_success = False

        else:
            for remote in remotes:
                if task.get("status") == "ABORTED":
                    break
                log_label = f"⚡ Transmitting to {remote}..."
                step_ok = self._execute_rclone_step(task, remote, source_dir, files, False, log_label)
                if not step_ok:
                    overall_success = False

        duration = round(time.time() - t0, 2)
        task["completed"] = True
        if overall_success and task.get("status") != "ABORTED":
            final_status = "SUCCESS"
        elif task.get("status") == "ABORTED":
            final_status = "ABORTED"
        else:
            final_status = "ERROR"
        task["status"] = final_status

        msg_queue.put({
            "event": "complete",
            "data": {
                "task_id": task_id,
                "status": final_status,
                "duration_seconds": duration,
                "dry_run": dry_run
            }
        })

    def _force_kill(self, proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def _format_relative_time(delta_seconds: float) -> str:
        if delta_seconds < 60:
            return "Just now"
        elif delta_seconds < 3600:
            return f"{int(delta_seconds // 60)}m ago"
        elif delta_seconds < 86400:
            return f"{int(delta_seconds // 3600)}h ago"
        return f"{int(delta_seconds // 86400)}d ago"


sync_service = SovereignSyncService(dropzone_dir=SYNC_DROPZONE_DIR)


SYNC_HTML_TEMPLATE = load_template("sync_cockpit.html")


@bp.route('/sync', methods=['GET'])
def route_sync_cockpit():
    """Renders the Sovereign Sync Cockpit (Tool #43)."""
    return render_template_string(SYNC_HTML_TEMPLATE)


@bp.route('/api/sync/envelopes', methods=['GET'])
def api_sync_envelopes():
    """Returns list of all configured envelopes with file counts and status."""
    return jsonify(sync_service.get_envelopes_summary())


@bp.route('/api/sync/staged', methods=['GET'])
def api_sync_staged():
    """Returns JSON inventory of files currently in the specified envelope."""
    envelope = request.args.get("envelope")
    return jsonify(sync_service.get_staged_inventory(envelope_key=envelope))


@bp.route('/api/sync/execute', methods=['POST'])
def api_sync_execute():
    """Dispatches asynchronous rclone sync task."""
    data = request.get_json(silent=True) or {}
    envelope = data.get("envelope")
    target = data.get("target")
    files = data.get("files") or data.get("selected_files")
    dry_run = bool(data.get("dry_run", False))
    clean_mode = bool(data.get("clean_mode", True))

    if envelope == "ALL" or data.get("sync_all"):
        def run_all_sync():
            try:
                subprocess.run(["/bin/bash", "/home/james/SovereignOS/scripts/sync_to_gdrive.sh"], capture_output=True, text=True, timeout=120)
            except Exception as e:
                logger.error(f"Error executing sync_to_gdrive: {e}")
        threading.Thread(target=run_all_sync, daemon=True).start()
        return jsonify({
            "status": "dispatched",
            "task_id": "all-envelopes-sync",
            "envelope": "ALL",
            "message": "Full Sovereign Drive Sync dispatched successfully."
        })

    try:
        task_id = sync_service.dispatch_sync(
            envelope_key=envelope,
            target_key=target,
            selected_files=files,
            clean_mode=clean_mode,
            dry_run=dry_run
        )
        return jsonify({
            "status": "dispatched",
            "task_id": task_id,
            "envelope": envelope,
            "target": target,
            "clean_mode": clean_mode,
            "dry_run": dry_run
        })
    except Exception as e:
        logger.error("Sync dispatch failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 400


@bp.route('/api/sync/prune-clutter', methods=['POST'])
def api_sync_prune_clutter():
    """Accepts envelope, deletes local non-source clutter (.png, .html, etc.) and empty subdirectories."""
    data = request.get_json(silent=True) or {}
    envelope_key = data.get("envelope")
    if not envelope_key:
        return jsonify({"status": "error", "message": "Missing envelope parameter"}), 400

    try:
        result = sync_service.prune_local_clutter(envelope_key)
        return jsonify(result)
    except Exception as e:
        logger.error("Prune clutter failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 400


@bp.route('/api/sync/stream/<task_id>', methods=['GET'])
def api_sync_stream(task_id: str):
    """Server-Sent Events streaming telemetry connection."""
    return Response(
        sync_service.stream_telemetry(task_id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@bp.route('/api/sync/abort/<task_id>', methods=['POST'])
def api_sync_abort(task_id: str):
    """Emergency abort endpoint for running sync tasks."""
    aborted = sync_service.abort_task(task_id)
    return jsonify({"status": "aborted" if aborted else "not_found", "task_id": task_id})


@bp.route('/api/drive/sync-inbox', methods=['POST'])
def api_drive_sync_inbox():
    """Triggers drive_drop_bridge.py --once asynchronously."""
    def run_bridge():
        try:
            logger.info("Executing Google Drive Drop Bridge via API trigger...")
            py_bin = "/home/james/SovereignOS/.venv/bin/python3"
            script_path = "/home/james/SovereignOS/scripts/drive_drop_bridge.py"
            subprocess.run([py_bin, script_path, "--once"], capture_output=True, text=True, timeout=120)
        except Exception as e:
            logger.error(f"Error executing drive drop bridge: {e}")

    threading.Thread(target=run_bridge, daemon=True).start()
    return jsonify({"status": "dispatched", "message": "Google Drive Inbox pull triggered asynchronously."})

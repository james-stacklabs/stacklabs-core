#!/usr/bin/env python3
"""
Sovereign OS: Sysfs-Style VFS CMDB Materializer
Maps Fleet Configuration Items (CIs) into a pure POSIX directory tree.
Attributes are atomic 1-line text files. Relationships are POSIX symlinks.
"""
import os
import shutil
import sys
from pathlib import Path

VFS_CMDB_PERSIST = Path("/home/james/stacklabs/vfs/cmdb")
VFS_CMDB_SHM = Path("/dev/shm/faas_vfs/cmdb")

def write_atomic(filepath: Path, content: str):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(str(content).strip() + "\n", encoding="utf-8")

def create_symlink(source: Path, link_name: Path):
    link_name.parent.mkdir(parents=True, exist_ok=True)
    if link_name.is_symlink() or link_name.is_file():
        link_name.unlink()
    elif link_name.is_dir():
        shutil.rmtree(link_name)
    # Compute relative path for portable symlinks
    rel_path = os.path.relpath(source, link_name.parent)
    link_name.symlink_to(rel_path)

def materialize_tree(root: Path):
    root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. PHYSICAL NODES (/cmdb/physical)
    # -------------------------------------------------------------
    phys = root / "physical"
    
    # clio
    clio = phys / "clio"
    write_atomic(clio / "id.txt", "hw_clio")
    write_atomic(clio / "role.txt", "forge_master")
    write_atomic(clio / "silicon.txt", "AMD Ryzen 7 7735HS (8C/16T)")
    write_atomic(clio / "ram_gb.txt", "32")
    write_atomic(clio / "storage.txt", "1TB NVMe PCIe 4.0")
    write_atomic(clio / "ip.txt", "100.73.155.70")
    write_atomic(clio / "lan_ip.txt", "192.168.1.183")
    write_atomic(clio / "os.txt", "Ubuntu 24.04 LTS")
    write_atomic(clio / "status.txt", "ACTIVE")
    write_atomic(clio / "avatar.txt", "/avatars/cmdb/clio_owl.png")

    # artemis
    artemis = phys / "artemis"
    write_atomic(artemis / "id.txt", "hw_artemis")
    write_atomic(artemis / "role.txt", "cuda_transcode_node")
    write_atomic(artemis / "gpu.txt", "NVIDIA GeForce GTX 1060 6GB GDDR5")
    write_atomic(artemis / "vram_mb.txt", "6144")
    write_atomic(artemis / "cuda_version.txt", "13.0")
    write_atomic(artemis / "driver_version.txt", "580.178.04")
    write_atomic(artemis / "nvenc_encoders.txt", "h264_nvenc, hevc_nvenc, av1_nvenc")
    write_atomic(artemis / "ip.txt", "100.108.185.53")
    write_atomic(artemis / "lan_ip.txt", "192.168.1.64")
    write_atomic(artemis / "status.txt", "ACTIVE")
    write_atomic(artemis / "avatar.txt", "/avatars/cmdb/artemis_huntress.png")

    # pegasus
    pegasus = phys / "pegasus"
    write_atomic(pegasus / "id.txt", "hw_pegasus")
    write_atomic(pegasus / "role.txt", "bedroom_theater_terminal")
    write_atomic(pegasus / "display.txt", "65-inch 4K Silk TV")
    write_atomic(pegasus / "browser.txt", "Amazon Silk")
    write_atomic(pegasus / "ip.txt", "100.96.77.20")
    write_atomic(pegasus / "lan_ip.txt", "192.168.1.200")
    write_atomic(pegasus / "status.txt", "ACTIVE")

    # tapo c120
    c120 = phys / "c120"
    write_atomic(c120 / "id.txt", "hw_tapo_c120")
    write_atomic(c120 / "role.txt", "smyrna_optical_sentry")
    write_atomic(c120 / "lan_ip.txt", "192.168.1.191")
    write_atomic(c120 / "resolution.txt", "1080p")
    write_atomic(c120 / "fps.txt", "20")
    write_atomic(c120 / "rtsp.url", "rtsp://192.168.1.191:554/stream2")
    write_atomic(c120 / "http_stream.url", "/api/vfs/cameras/c120/stream")
    write_atomic(c120 / "status.txt", "ACTIVE")

    # argo
    argo = phys / "argo"
    write_atomic(argo / "id.txt", "hw_argo")
    write_atomic(argo / "role.txt", "vision_sensor_sentry")
    write_atomic(argo / "silicon.txt", "Raspberry Pi 5 (8GB) + Hailo-8L NPU (13 TOPS)")
    write_atomic(argo / "ip.txt", "100.111.248.60")
    write_atomic(argo / "status.txt", "ACTIVE")

    # -------------------------------------------------------------
    # 2. LOGICAL SERVICES (/cmdb/logical)
    # -------------------------------------------------------------
    log = root / "logical"

    # faas_server
    faas = log / "faas_server"
    write_atomic(faas / "id.txt", "svc_faas_server")
    write_atomic(faas / "service.txt", "faas_server.service")
    write_atomic(faas / "port.txt", "3033")
    write_atomic(faas / "internal_port.txt", "3032")
    write_atomic(faas / "protocol.txt", "HTTP/1.1 + Starlette VFS")
    write_atomic(faas / "public_url.txt", "https://faas.stacklabsllc.com")
    write_atomic(faas / "status.txt", "ACTIVE")
    create_symlink(clio, faas / "runs_on")

    # stacklabs_retina
    retina = log / "stacklabs_retina"
    write_atomic(retina / "id.txt", "svc_stacklabs_retina")
    write_atomic(retina / "service.txt", "stacklabs-retina.service")
    write_atomic(retina / "port.txt", "3028")
    write_atomic(retina / "protocol.txt", "HTTP/1.1 MJPEG Multipart")
    write_atomic(retina / "status.txt", "ACTIVE")
    create_symlink(clio, retina / "runs_on")
    create_symlink(c120, retina / "ingests_from")

    # stream_sniper
    sniper = log / "stream_sniper"
    write_atomic(sniper / "id.txt", "svc_stream_sniper")
    write_atomic(sniper / "service.txt", "stream_sniper_daemon.service")
    write_atomic(sniper / "port.txt", "5056")
    write_atomic(sniper / "buffer_path.txt", "/dev/shm/stream_sniper")
    write_atomic(sniper / "status.txt", "ACTIVE")
    create_symlink(clio, sniper / "runs_on")
    create_symlink(artemis, sniper / "transcribes_on")

    # clio_queue_watcher
    watcher = log / "clio_queue_watcher"
    write_atomic(watcher / "id.txt", "svc_clio_queue_watcher")
    write_atomic(watcher / "service.txt", "clio_queue_watcher.service")
    write_atomic(watcher / "runner.txt", "agy")
    write_atomic(watcher / "queue_path.txt", "/home/james/stacklabs/queue")
    write_atomic(watcher / "status.txt", "ACTIVE")
    create_symlink(clio, watcher / "runs_on")

    # cmdb_studio
    studio = log / "cmdb_studio"
    write_atomic(studio / "id.txt", "svc_cmdb_studio")
    write_atomic(studio / "port.txt", "3025")
    write_atomic(studio / "backend_proxy.txt", "http://127.0.0.1:8095")
    write_atomic(studio / "status.txt", "ACTIVE")
    create_symlink(clio, studio / "runs_on")

    # -------------------------------------------------------------
        print(f'Synced {root}')

def main():
    pass

if __name__ == '__main__':
    main()

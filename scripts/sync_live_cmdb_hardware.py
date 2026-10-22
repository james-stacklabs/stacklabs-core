import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def cleanup_and_sync():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Delete all old hardware records
    cur.execute("DELETE FROM cmdb_ci_hardware WHERE sys_id LIKE 'hw_%' OR sys_id LIKE 'ci_%' OR sys_id IN ('clio', 'argo', 'calvin', 'hobbes', 'mando', 'metsy-prime', 'grogu', 'grogu-1', 'c120-webcam', 'clio-webcam-1', 'clio-suzie-q');")
    cur.execute("DELETE FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_hardware' AND (sys_id LIKE 'hw_%' OR sys_id LIKE 'ci_%' OR name IN ('clio', 'argo', 'calvin', 'hobbes', 'mando', 'metsy-prime', 'grogu', 'grogu-1', 'c120-webcam', 'clio-webcam-1', 'clio-suzie-q', 'stumpy', 'mobile-james', 'mobile-barb', 'beelink', 'artemis', 'pegasus', 'desktop-bintles-1', 'rudnickidell', 'pixel-10a', 'pixel-7-pro', 'barbaras-s23-ultra', 'ipad-gen-7', 'jamess-tv', 'jamess-2nd-tv', 'C120', 'nexigo-n60-webcam'));")
    
    # 2. Canonical Clean Dataset
    records = [
        # (sys_id, name, short_description, operational_status, assigned_to, ip_address, mac_address, model_id, u_avatar_url)
        (
            'hw_clio_beelink_r7', 'clio',
            'Beelink SER Mini PC (AMD Ryzen 7 7735HS 8C/16T, 32GB DDR5 RAM, 1TB NVMe, NexiGo N60 Webcam, Ubuntu 24.04 LTS) - Sovereign Master Core Hub',
            1, 'james', '100.73.155.70', 'eno1',
            'Beelink SER Mini PC (AMD Ryzen 7 7735HS 8C/16T, 32GB RAM, 1TB NVMe, Ubuntu 24.04 LTS)',
            '/avatars/cmdb/clio_owl.png'
        ),
        (
            'hw_argo_rpi5_hailo', 'argo',
            'Raspberry Pi 5 Model B Rev 1.0 (8GB RAM, BCM2712 Quad-Core 2.4GHz) with Hailo-10H PCIe AI Processor NPU - Living Room 65" TV Vision Kiosk (The ONLY Pi 5)',
            1, 'james', '100.111.248.60', '192.168.1.150',
            'Raspberry Pi 5 Model B Rev 1.0 (8GB RAM) + Hailo-10H PCIe AI Processor NPU',
            '/avatars/cmdb/argo_vessel.png'
        ),
        (
            'hw_grogu_pizero2w', 'grogu-1',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) with TI PCM2902 USB Audio Codec (SuzyPi Mic Array) - Mobile Acoustic Sentinel',
            1, 'james', '100.68.247.36', '192.168.1.185',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) + TI PCM2902 Audio Codec',
            '/avatars/cmdb/grogu_pod.png'
        ),
        (
            'hw_mando_pizero2w', 'mando',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) - Smyrna Local Edge Sentinel',
            1, 'james', '100.120.34.87', '192.168.1.153',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53)',
            '/avatars/cmdb/mando_sentinel.png'
        ),
        (
            'hw_calvin_pizero2w', 'calvin',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) - Barb''s House Edge Sentinel & GardenStack Relay',
            1, 'barb', '100.104.14.75', '192.168.1.152',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53)',
            '/avatars/cmdb/calvin_kid.png'
        ),
        (
            'hw_hobbes_pizero2w', 'hobbes',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) with icSpring USB Camera - Mother''s House Edge Sentinel & Camera',
            1, 'mother', '100.88.5.122', '2600:6c5a:597f:5a95::13ea',
            'Raspberry Pi Zero 2 W Rev 1.0 (512MB RAM, Cortex-A53) + icSpring USB Camera',
            '/avatars/cmdb/hobbes_tiger.png'
        ),
        (
            'hw_metsy_prime_rpi3', 'metsy-prime',
            'Raspberry Pi 3 Model B Rev 1.2 (1GB RAM, BCM2837 Cortex-A53) - Cozy Card Kiosk & 16-Bit UAT Bench',
            1, 'james', '100.122.254.110', '192.168.1.186',
            'Raspberry Pi 3 Model B Rev 1.2 (1GB RAM, BCM2837 Cortex-A53)',
            '/avatars/cmdb/metsy_prime.png'
        ),
        (
            'hw_artemis_msi_win10', 'artemis',
            'MSI Gaming Workstation Laptop (Intel i7, NVIDIA RTX, Windows 10 Pro) - Pilot Primary IDE & Telemetry Workstation',
            1, 'james', '100.70.84.19', '192.168.1.64',
            'MSI Gaming Workstation Laptop (Intel i7, NVIDIA RTX, Windows 10 Pro)',
            '/avatars/cmdb/artemis_huntress.png'
        ),
        (
            'hw_pegasus_win10', 'pegasus',
            'Secondary Dev Workstation & Compute Node (Windows 10 Laptop)',
            1, 'james', '100.90.6.117', '192.168.1.177',
            'Secondary Dev Laptop (Windows 10)',
            None
        ),
        (
            'hw_desktop_bintles', 'desktop-bintles-1',
            'Family Desktop Workstation (Windows 11)',
            2, 'eileen', '100.119.151.126', '',
            'Desktop PC (Windows 11)',
            None
        ),
        (
            'hw_c120_cam_node', 'C120',
            'C120 Local Camera Node (192.168.1.191, MAC 8c:86:dd:e7:27:65)',
            1, 'james', '192.168.1.191', '8c:86:dd:e7:27:65',
            'C120 Local Camera Node (192.168.1.191)',
            None
        ),
        (
            'hw_nexigo_n60_webcam', 'nexigo-n60-webcam',
            'NexiGo N60 FHD 1080p USB Webcam attached to Clio',
            1, 'james', '100.73.155.70', 'usb-nexigo-n60',
            'NexiGo N60 FHD 1080p USB Webcam',
            None
        ),
        (
            'hw_pixel_10a', 'pixel-10a',
            'Google Pixel 10a (Android) - Pilot Primary Mobile Command & Field Telemetry Device',
            1, 'james', '100.102.4.40', '',
            'Google Pixel 10a (Android)',
            None
        ),
        (
            'hw_pixel_7_pro', 'pixel-7-pro',
            'Google Pixel 7 Pro (Android) - Pilot Secondary Mobile Device',
            2, 'james', '100.123.176.125', '',
            'Google Pixel 7 Pro (Android)',
            None
        ),
        (
            'hw_barbara_s23_ultra', 'barbaras-s23-ultra',
            'Samsung Galaxy S23 Ultra (Android) - Barb Mobile Telemetry & Sentinel Ingress',
            2, 'barb', '100.70.12.50', '',
            'Samsung Galaxy S23 Ultra (Android)',
            None
        ),
        (
            'hw_ipad_gen_7', 'ipad-gen-7',
            'Apple iPad 7th Gen (iOS) - Family Tablet Outpost',
            2, 'eileen', '100.112.189.71', '',
            'Apple iPad 7th Gen (iOS)',
            None
        ),
        (
            'hw_jamess_tv', 'jamess-tv',
            'Primary Living Room 65" Cinema Display (Fire TV / Android)',
            2, 'james', '100.76.78.11', '',
            'Fire TV Smart Display 65" (Android)',
            None
        ),
        (
            'hw_jamess_2nd_tv', 'jamess-2nd-tv',
            'Secondary Bedroom Cinema Display (Fire TV / Android)',
            2, 'james', '100.122.250.100', '',
            'Fire TV Smart Display Bedroom (Android)',
            None
        )
    ]
    
    for sys_id, name, desc, status, assigned, ip, mac, model, avatar in records:
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to, sys_created_on, sys_updated_on)
            VALUES (?, ?, 'cmdb_ci_hardware', ?, ?, ?, datetime('now'), datetime('now'));
        """, (sys_id, name, desc, status, assigned))
        
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_hardware (sys_id, ip_address, mac_address, model_id, u_avatar_url, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'));
        """, (sys_id, ip, mac, model, avatar))
        
    conn.commit()
    conn.close()
    print("[+] CMDB database purged of stale records and cleanly synchronized.")

if __name__ == "__main__":
    cleanup_and_sync()

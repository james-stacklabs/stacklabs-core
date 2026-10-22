#!/usr/bin/env python3
"""
Sovereign OS — Register Barf Authentic Puppet Canonical Anchor
Path: scripts/register_barf_canonical_anchor.py

Registers the authentic physical Barf terrier puppet photo (shot_6_close-up_portrait.jpg)
into cmdb_ci_media_asset and sys_media_asset via scripts/core/api_client.py REST endpoints.
Purges synthetic/CGI/Deadpool references.
"""

import os
import sys
import hashlib

sys.path.append("/home/james/stacklabs/scripts")
from core import api_client

ANCHOR_V2 = "/home/james/stacklabs/dna/assets/barf_anchor_v2.jpg"
FANSTACK_AVATAR = "/home/james/stacklabs/15_FanStackCreator/public/assets/avatars/barf.jpg"
CHARACTER_MAP = "/home/james/stacklabs/15_FanStackCreator/public/assets/character_maps/barf_anchor.jpg"
AVATAR_ROOT = "/home/james/stacklabs/avatars/barf.jpg"

def main():
    print("🚀 [BARF-ANCHOR-REGISTER] Ingesting authentic puppet anchor into Sovereign CMDB & Media Asset registry...")
    
    if not os.path.exists(ANCHOR_V2):
        print(f"❌ Error: Canonical anchor file not found at {ANCHOR_V2}")
        sys.exit(1)
        
    with open(ANCHOR_V2, "rb") as f:
        data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()
        md5 = hashlib.md5(data).hexdigest()
        size = len(data)
        
    print(f"  📦 File: {ANCHOR_V2}")
    print(f"  🔒 SHA256: {sha256}")
    print(f"  🏷️ MD5: {md5}")
    print(f"  📏 Size: {size:,} bytes")
    
    # Register core expressions
    registrations = [
        ("canonical_anchor", ANCHOR_V2, "Canonical Puppet Anchor (shot_6)"),
        ("avatar", FANSTACK_AVATAR, "Canonical FanStack Avatar"),
        ("character_map", CHARACTER_MAP, "Canonical Puppet Character Map"),
        ("front_neutral", AVATAR_ROOT, "Authentic Puppet Front Neutral"),
        ("prime_avatar", "/assets/avatars/barf.jpg", "Prime Puppet Avatar")
    ]
    
    for expr, path, name in registrations:
        res = api_client.register_media_asset(
            advocate="barf",
            expression=expr,
            file_path=path,
            sha256=sha256,
            category="Canonical Anchor",
            mime_type="image/jpeg",
            name=f"Barf {name}"
        )
        print(f"  ✔ Registered [{expr}]: {res.get('status')} (sys_id={res.get('sys_id')})")
        
    # Verify assets via api_client
    assets = api_client.get_media_assets(advocate="barf")
    print(f"🎉 Barf media asset registry verified. Total assets: {assets.get('count')}")

if __name__ == "__main__":
    main()

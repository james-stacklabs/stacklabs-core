#!/home/james/stacklabs/.venv/bin/python3
"""
Restores /opt/antigravity/antigravity.svg with a high-contrast '2.0' Cockpit badge
so Antigravity 2.0 (WM_CLASS=antigravity) displays a visible, distinct icon in the Ubuntu GNOME dock.
"""

import pathlib
import subprocess
import sys

SOURCE_SVG = pathlib.Path("/opt/antigravity-ide/antigravity.svg")
TARGET_SVG = pathlib.Path("/opt/antigravity/antigravity.svg")
LOCAL_DESKTOP = pathlib.Path("/home/james/.local/share/applications/antigravity.desktop")

BADGE_OVERLAY = """
  <g id="cockpit_2_badge">
    <rect x="460" y="610" width="400" height="240" rx="64" fill="#0B0D13" stroke="#10B981" stroke-width="24"/>
    <text x="660" y="772" text-anchor="middle" fill="#10B981" font-family="Inter, Ubuntu, sans-serif" font-weight="900" font-size="148" letter-spacing="-4">2.0</text>
  </g>
</svg>
"""

DESKTOP_CONTENT = """[Desktop Entry]
Name=Antigravity 2.0 Cockpit
GenericName=Agentic AI Cockpit
Comment=Antigravity 2.0 - Google Agentic Desktop Application
Exec=/opt/antigravity/antigravity --no-sandbox --disable-gpu %U
Icon=/opt/antigravity/antigravity.svg
Terminal=false
Type=Application
Categories=Development;IDE;TextEditor;
StartupWMClass=antigravity
MimeType=x-scheme-handler/antigravity;
Keywords=google;antigravity;ai;agentic;coding;cockpit;
Actions=Headless;

[Desktop Action Headless]
Name=Launch Headless Remote Server
Exec=env ELECTRON_OZONE_PLATFORM_HINT=headless /opt/antigravity/antigravity --headless
"""


def main() -> int:
    if not SOURCE_SVG.exists():
        sys.stderr.write(f"ERROR: Source SVG not found at {SOURCE_SVG}\n")
        return 1

    raw_svg = SOURCE_SVG.read_text(encoding="utf-8")
    if "</svg>" not in raw_svg:
        sys.stderr.write("ERROR: Malformed SVG in source file\n")
        return 1

    badged_svg = raw_svg.replace("</svg>", BADGE_OVERLAY)
    TARGET_SVG.write_text(badged_svg, encoding="utf-8")
    print(f"Wrote badged Antigravity 2.0 icon to {TARGET_SVG} ({TARGET_SVG.stat().st_size} bytes)")

    LOCAL_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_DESKTOP.write_text(DESKTOP_CONTENT, encoding="utf-8")
    print(f"Updated desktop entry at {LOCAL_DESKTOP}")

    subprocess.run(
        ["update-desktop-database", str(LOCAL_DESKTOP.parent)],
        check=False,
    )

    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_favs = res.stdout.strip()
        if "antigravity.desktop" not in current_favs and current_favs.endswith("]"):
            if "'antigravity-ide.desktop'" in current_favs:
                updated_favs = current_favs.replace(
                    "'antigravity-ide.desktop'",
                    "'antigravity-ide.desktop', 'antigravity.desktop'",
                    1,
                )
            else:
                updated_favs = current_favs[:-1] + ", 'antigravity.desktop']"
            subprocess.run(
                ["gsettings", "set", "org.gnome.shell", "favorite-apps", updated_favs],
                check=True,
            )
            print(f"Pinned antigravity.desktop to GNOME dock: {updated_favs}")
        else:
            print(f"GNOME dock favorites already include antigravity.desktop: {current_favs}")
    except Exception as exc:
        print(f"Note: gsettings update skipped or non-fatal: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

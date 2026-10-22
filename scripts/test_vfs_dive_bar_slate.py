#!/home/james/stacklabs/.venv/bin/python3
"""
Test Harness for 5-Advocate Sunday Night Dive Bar
Path: /home/james/stacklabs/scripts/test_vfs_dive_bar_slate.py
"""
import json
import os
import pathlib
import subprocess
import time

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
ADVOCATES = [
    ROOT_DIR / "vfs" / "advocates" / "barf_discord",
    ROOT_DIR / "vfs" / "advocates" / "lone_star_larry",
    ROOT_DIR / "vfs" / "advocates" / "cheesehead_chet",
    ROOT_DIR / "vfs" / "advocates" / "burl_discord",
    ROOT_DIR / "vfs" / "advocates" / "sammy_savant",
]
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python3"

def run_cmd(args, cwd):
    res = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def main():
    print("==================================================")
    print("⚡ VERIFYING 5-ADVOCATE SUNDAY NIGHT DIVE BAR")
    print("==================================================")

    for adv in ADVOCATES:
        spec_path = adv / "spec.json"
        verify_path = adv / "verify.sh"
        run_path = adv / "run.py"
        
        assert spec_path.exists(), f"Missing spec.json in {adv.name}"
        assert verify_path.exists(), f"Missing verify.sh in {adv.name}"
        assert run_path.exists(), f"Missing run.py in {adv.name}"
        
        # Test verify.sh syntax
        rc, out, err = run_cmd(["bash", "-n", "verify.sh"], adv)
        assert rc == 0, f"Bash syntax error in {adv.name}/verify.sh: {err}"
        
        # Test run.py syntax
        rc, out, err = run_cmd([str(PYTHON_BIN), "-m", "py_compile", "run.py"], adv)
        assert rc == 0, f"Python syntax error in {adv.name}/run.py: {err}"
        
        print(f"✓ {adv.name}: spec.json, verify.sh, and run.py verified")

    print("\n✅ ALL 5 DIVE BAR ADVOCATES READY FOR SUNDAY NIGHT FOOTBALL")
    print("==================================================")

if __name__ == "__main__":
    main()

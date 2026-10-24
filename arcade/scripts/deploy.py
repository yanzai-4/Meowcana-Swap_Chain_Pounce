"""One-command deploy to the UNO Q over ADB: pack assets, build the app ZIP, push it, run the flash script.

  python scripts/deploy.py                  # pack + zip + push + flash (compiles the sketch on the board)
  python scripts/deploy.py --bench          # same, but the app runs python/bench.py (TFT/RPC benchmark)
  python scripts/deploy.py --bench --fast-bus   # benchmark library bus vs direct GPIO modes 1-3 (see README)
  python scripts/deploy.py --fast-bus       # the game with the direct-GPIO TFT bus (default mode 3)
  python scripts/deploy.py --zip-only       # just build/uno-q-arcade.zip
  python scripts/deploy.py --logs           # follow the Python log afterwards

Board serial: --serial, or $ARCADE_SERIAL, or the only ADB device. ADB: --adb or $ADB or `adb` on PATH.
The first compile on the board needs Internet access for the Arduino libraries (a few minutes).
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "build" / "uno-q-arcade.zip"
REMOTE_ZIP = "/tmp/uno-q-arcade.zip"
REMOTE_FLASH = "/tmp/uno-q-flash-lf.sh"
PACKAGED = ("app.yaml", "python", "sketch")
SKIP_PARTS = {"__pycache__", ".venv", "build", "tests"}
SKIP_SUFFIXES = (".pyc", ".DS_Store")
# python/main.py replacement for --bench. stdout is also copied to <app>/data/bench.log, because
# `docker logs` on the board can fail with "invalid character '\x00'"; read it with
# adb shell cat ~/ArduinoApps/uno-q-arcade-cli/data/bench.log
BENCH_MAIN = b'''import os
import sys


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(_data, exist_ok=True)
sys.stdout = _Tee(sys.stdout, open(os.path.join(_data, "bench.log"), "w", encoding="utf-8"))

from bench import main

main()
'''


def build_zip(bench, fast_bus):
    ZIP.parent.mkdir(exist_ok=True)
    ZIP.unlink(missing_ok=True)
    count = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in PACKAGED:
            path = ROOT / name
            files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
            for file in files:
                rel = file.relative_to(ROOT)
                if SKIP_PARTS & set(rel.parts[1:]) or rel.name.endswith(SKIP_SUFFIXES):
                    continue
                data = file.read_bytes()
                if bench and rel.as_posix() == "python/main.py":
                    data = BENCH_MAIN
                if fast_bus and rel.as_posix() == "sketch/sketch.ino":
                    text = data.decode("utf-8")
                    flag = "#define ARCADE_FAST_BUS 0"
                    if flag not in text:
                        raise SystemExit("sketch.ino: ARCADE_FAST_BUS default line not found")
                    data = text.replace(flag, "#define ARCADE_FAST_BUS 1", 1).encode("utf-8")
                archive.writestr(rel.as_posix(), data)
                count += 1
    print(f"{ZIP} ({count} files, {ZIP.stat().st_size / 1024:.0f} KB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serial", default=os.environ.get("ARCADE_SERIAL"))
    parser.add_argument("--adb", default=os.environ.get("ADB") or shutil.which("adb") or "adb")
    parser.add_argument("--bench", action="store_true", help="run python/bench.py instead of the game")
    parser.add_argument("--fast-bus", action="store_true",
                        help="build the sketch with ARCADE_FAST_BUS 1 (direct GPIO TFT bus, default mode 3)")
    parser.add_argument("--zip-only", action="store_true")
    parser.add_argument("--logs", action="store_true", help="follow the app log after flashing")
    parser.add_argument("--skip-pack", action="store_true", help="do not re-run tools/pack_assets.py")
    args = parser.parse_args()

    if not args.skip_pack:
        subprocess.run([sys.executable, str(ROOT / "tools" / "pack_assets.py")], check=True, cwd=ROOT)
    build_zip(args.bench, args.fast_bus)
    if args.zip_only:
        return
    adb = [args.adb] + (["-s", args.serial] if args.serial else ["-d"])
    # flash.sh without CRLFs (the board's sh rejects them), pushed next to the ZIP.
    script = ROOT / "scripts" / "flash.sh"
    lf = ROOT / "build" / "flash-lf.sh"
    lf.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))
    for cmd in (adb + ["push", str(ZIP), REMOTE_ZIP], adb + ["push", str(lf), REMOTE_FLASH],
                adb + ["shell", "-T", f"sh {REMOTE_FLASH} {REMOTE_ZIP}"]):
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True)
    if args.logs:
        subprocess.run(adb + ["shell", "-t", 'TMPDIR=/tmp arduino-app-cli app logs '
                              '"$HOME/ArduinoApps/uno-q-arcade-cli" --follow'])


if __name__ == "__main__":
    main()

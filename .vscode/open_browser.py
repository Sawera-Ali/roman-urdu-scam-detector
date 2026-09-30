"""Start a detached browser waiter so VS Code can immediately launch Flask."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:5000"
ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / ".venv" / "browser-launch.log"


def wait_for_server(timeout=120, url=URL):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.25)
    return False


def open_when_ready():
    print(f"Waiting for {URL}", flush=True)
    if not wait_for_server():
        print("Flask did not respond within 120 seconds. Check the application terminal.", flush=True)
        return 1
    try:
        # Windows ShellExecute uses the user's HTTP association: an external
        # default browser, never VS Code's Simple Browser or a BROWSER override.
        os.startfile(URL)
    except OSError as error:
        print(f"Windows could not open the default browser: {error}", flush=True)
        return 1
    print(f"Opened {URL} using the Windows default browser.", flush=True)
    return 0


def main():
    if sys.argv[1:] == ["--wait"]:
        return open_when_ready()
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", 5000)) == 0:
            print("Port 5000 is already in use. Stop the existing server before launching another instance.", flush=True)
            return 1
    # The short preLaunchTask exits immediately. The detached worker survives
    # task completion and polls while VS Code launches app/app.py independently.
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    with LOG.open("w", encoding="utf-8") as log:
        subprocess.Popen(
            [str(pythonw), str(Path(__file__).resolve()), "--wait"],
            cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    print(f"Browser watcher started. Diagnostic log: {LOG}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

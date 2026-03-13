import os
import subprocess
import sys
import time
import signal
import atexit
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# ... (parse_jobs remains the same) ...
# ----------------------------
# Job parsing
# ----------------------------
def parse_jobs(jobfile: Path) -> List[Dict[str, str]]:
    jobs = []
    current = {}

    with jobfile.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                if current:
                    jobs.append(current)
                    current = {}
                continue
            if line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            current[k.strip()] = v.strip()
        if current:
            jobs.append(current)

    return jobs


STATUS_FILE = "job_status_2.log"

def log_status(message: str):
    """Writes a timestamped message to the shared status file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Using 'a' (append) mode is key for shared access
    with open(STATUS_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def run_jobs(jobs: list, max_parallel: int):
    running = []
    job_iter = iter(jobs)

    def cleanup():
        if not running: return
        log_status("!!! SCRIPT INTERRUPTED - Killing all active jobs...")
        for p, label in running:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except: pass

    atexit.register(cleanup)

    def launch(job):
        label = job.get("LABEL", "unnamed")
        cmd = job["CMD"]
        log_status(f"START: {label} (CMD: {cmd})")
        print(f"[START] {label}")
        
        # We still use os.setsid to ensure we can kill child sub-processes
        p = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL, # Keep console clean
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        return p, label

    try:
        # Initial fill
        while len(running) < max_parallel:
            try:
                running.append(launch(next(job_iter)))
            except StopIteration: break

        # Main loop
        while running:
            time.sleep(1)
            for item in running[:]:
                p, label = item
                if p.poll() is not None:
                    status_msg = f"DONE:  {label} (Exit Code: {p.returncode})"
                    log_status(status_msg)
                    print(f"[{status_msg}]")
                    
                    running.remove(item)
                    try:
                        running.append(launch(next(job_iter)))
                    except StopIteration: pass

    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == "__main__":
    # Usage: python runner.py jobs.txt 4
    if len(sys.argv) < 2:
        sys.exit("Usage: ./runner.py <jobfile> [max_parallel]")
    
    # Initialize the log file with a session header
    log_status("="*40 + "\nNEW SESSION STARTED")
    run_jobs(parse_jobs(Path(sys.argv[1])), int(sys.argv[2]) if len(sys.argv) > 2 else 2)

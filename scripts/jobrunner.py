#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict

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

# ----------------------------
# Runner
# ----------------------------
def run_jobs(jobs: List[Dict[str, str]], max_parallel: int):
    running = []
    job_iter = iter(jobs)

    def launch(job):
        label = job.get("LABEL", "unnamed")
        cmd = job["CMD"]
        print(f"[START] {label}")
        p = subprocess.Popen(
            cmd,
            shell=True,
            preexec_fn=os.setsid
        )
        return p, label

    try:
        # Launch initial batch
        while len(running) < max_parallel:
            try:
                job = next(job_iter)
            except StopIteration:
                break
            running.append(launch(job))

        # Main loop
        while running:
            time.sleep(1)
            for p, label in list(running):
                if p.poll() is not None:
                    print(f"[DONE]  {label} (exit={p.returncode})")
                    running.remove((p, label))
                    try:
                        job = next(job_iter)
                        running.append(launch(job))
                    except StopIteration:
                        pass

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Killing all running jobs...")
        for p, _ in running:
            try:
                os.killpg(os.getpgid(p.pid), 15)
            except Exception:
                pass
        sys.exit(1)

# ----------------------------
# Entry
# ----------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_jobs.py jobs.txt [MAX_PARALLEL]")
        sys.exit(1)

    jobfile = Path(sys.argv[1])
    max_parallel = int(sys.argv[2]) if len(sys.argv) > 2 else os.cpu_count()

    jobs = parse_jobs(jobfile)
    print(f"[INFO] Loaded {len(jobs)} jobs")
    print(f"[INFO] Max parallel jobs = {max_parallel}")

    run_jobs(jobs, max_parallel)

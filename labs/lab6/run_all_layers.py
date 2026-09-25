#!/usr/bin/env python3
"""Run all 5 defence layers sequentially and summarise block/FP rates."""
import subprocess, json, re, sys

ROOT = "."
configs = [
    (None, "reports/0_baseline.json"),
    ([1], "reports/1_delimit.json"),
    ([1, 2], "reports/2_heuristic.json"),
    ([1, 2, 3], "reports/3_structured.json"),
    ([1, 2, 3, 4], "reports/4_privilege.json"),
    ([1, 2, 3, 4, 5], "reports/5_filtering.json"),
]

for layers, out_file in configs:
    print(f"Running layers={layers} -> {out_file}", flush=True)
    cmd = [r".venv\Scripts\python.exe", "labs/lab6/redteam.py", "--save", out_file]
    if layers is None:
        cmd.append("--no-guards")
    else:
        cmd += ["--layers"] + [str(l) for l in layers]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    stdout = result.stdout + result.stderr
    block = re.search(r"block rate\s+(\d+)/(\d+)\s*=\s*([\d.]+)", stdout)
    fp = re.search(r"false positives\s+(\d+)/(\d+)\s*=\s*([\d.]+)", stdout)
    priv = re.search(r"privileged calls\s+(\d+)", stdout)
    if result.returncode != 0:
        print(f"  ERROR (exit {result.returncode}): {stdout[-500:]}")
    else:
        print(f"  block={block.group(1)}/{block.group(2)}={block.group(3)}", end="  ")
        print(f"FP={fp.group(1)}/{fp.group(2)}={fp.group(3)}", end="  ")
        print(f"privileged={priv.group(1) if priv else '?'}")

print("\nAll done!", flush=True)

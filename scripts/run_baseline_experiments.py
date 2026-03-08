#!/usr/bin/env python3

"""Generate Sniper experiment jobfiles for single-core and multicore workloads."""

import argparse
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


TRACES: List[Tuple[str, str]] = [
    ("bc", "bc.sift"),
    ("bfs", "bfs.sift"),
    ("cc", "cc.sift"),
    ("tc", "tc.sift"),
    ("gc", "gc.sift"),
    ("pr", "pr.sift"),
    ("sssp", "sssp.sift"),
    ("rnd", "rnd.sift"),
    ("xs", "xs.sift"),
    ("dlrm", "dlrm.sift"),
    ("gen", "gen.sift"),
]

MULTICORE_WORKLOADS: Dict[str, List[List[str]]] = {
    "16": [
        [
            "cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift", "gen.sift", "gc.sift", "pr.sift",
            "cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift", "gen.sift", "gc.sift", "pr.sift",
        ],
        [
            "cc.sift", "cc.sift", "bfs.sift", "bfs.sift", "sssp.sift", "sssp.sift", "gen.sift", "gen.sift",
            "gc.sift", "gc.sift", "pr.sift", "pr.sift", "xs.sift", "xs.sift", "bc.sift", "bc.sift",
        ],
        [
            "dlrm.sift", "dlrm.sift", "dlrm.sift", "rnd.sift", "rnd.sift", "rnd.sift",
            "cc.sift", "cc.sift", "bfs.sift", "bfs.sift",
            "sssp.sift", "sssp.sift", "gen.sift", "gen.sift",
            "pr.sift", "xs.sift",
        ],
        [
            "cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift", "gen.sift", "gc.sift", "pr.sift",
            "xs.sift", "bc.sift", "tc.sift",
            "cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift",
        ],
    ],
    "8": [
        ["cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift", "gen.sift", "gc.sift", "pr.sift"],
        ["cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift", "sssp.sift", "gen.sift", "xs.sift", "bc.sift"],
        ["cc.sift", "bfs.sift", "dlrm.sift", "sssp.sift", "gen.sift", "pr.sift", "xs.sift", "tc.sift"],
        ["cc.sift", "rnd.sift", "gc.sift", "pr.sift", "xs.sift", "bc.sift", "tc.sift", "sssp.sift"],
    ],
    "4": [
        ["cc.sift", "bfs.sift", "dlrm.sift", "rnd.sift"],
        ["cc.sift", "sssp.sift", "gen.sift", "gc.sift"],
        ["bfs.sift", "dlrm.sift", "pr.sift", "xs.sift"],
        ["rnd.sift", "sssp.sift", "bc.sift", "tc.sift"],
    ],
    "2": [
        ["cc.sift", "bfs.sift"],
        ["dlrm.sift", "rnd.sift"],
        ["sssp.sift", "gen.sift"],
        ["gc.sift", "pr.sift"],
    ],
}

DEFAULT_IMAGE = "docker.io/kanell21/artifact_evaluation:victima"
SNIPER_COMMAND = "/app/sniper/run-sniper -s stop-by-icount:500000000 --genstats --power"

BASE_EXPERIMENTS: Dict[str, str] = {
    "baseline": "radix",
    "radix_perfect_pwc": "radix_perfect_pwc",
    "perfect": "perfecttlb",
    "vikram_both": "vikram_both",
    "vikram_fetch": "vikram_fetch",
    "vikram_ptb": "vikram_ptb",
    "victima": "victima",
    "utopia": "utopia",
    "potm": "potm",
    "tempo": "tempo",
    "vikram_special": "vikram_special",
    "vikram_both_special": "vikram_both_special",
    "vikram_ptb_64": "vikram_ptb_64",
    "vikram_ptb_128": "vikram_ptb_128",
    "vikram_ptb_256": "vikram_ptb_256",
    "radix_NoPwc": "radix_NoPwc",
    "vb_l1": "vb_l1",
    "vb_l2": "vb_l2",
    "vb_l3": "vb_l3",
    "vb_l2l3": "vb_l2l3",
    "vb_l1l2l3": "vb_l1l2l3",
}

VIRTUAL_EXPERIMENTS: Dict[str, str] = {
    "virt_baseline": "virt_radix",
    "virt_vikram_both": "virt_vikram_both",
    "virt_victima": "virt_victima",
    "virt_utopia": "virt_utopia",
    "virt_potm": "virt_potm",
    "virt_tempo": "virt_tempo",
}

MULTICORE_BASE_EXPERIMENTS: Dict[str, str] = {
    "baseline": "radix",
    "perfect": "perfecttlb",
    "vikram_both": "vikram_both",
    "vikram_fetch": "vikram_fetch",
    "vikram_ptb": "vikram_ptb",
    "victima": "victima",
    "utopia": "utopia",
    "potm": "potm",
    "tempo": "tempo",
    
    "vb_l1": "vb_l1",
    "vb_l2": "vb_l2",
    "vb_l3": "vb_l3",
    "vb_l2l3": "vb_l2l3",
    "vb_l1l2l3": "vb_l1l2l3",
}

def build_single_core_configs() -> Dict[str, Dict[str, str]]:
    configs: Dict[str, Dict[str, str]] = {}
    for label, cfg_name in {**BASE_EXPERIMENTS, **VIRTUAL_EXPERIMENTS}.items():
        configs[label] = {
            "config": f"/app/sniper/config/virtual_memory_configs/{cfg_name}.cfg",
            "label": label,
        }
    return configs


EXPERIMENT_CONFIGS = build_single_core_configs()


def build_multi_core_configs() -> Dict[str, Dict[str, str]]:
    configs: Dict[str, Dict[str, str]] = {}
    for cores in ("2", "4", "8", "16"):
        for label, cfg_name in MULTICORE_BASE_EXPERIMENTS.items():
            key = f"{cores}core_{label}"
            configs[key] = {
                "config": f"/app/sniper/config/virtual_memory_configs/{cores}core_{cfg_name}.cfg",
                "label": key,
            }
    return configs


MULTI_CORE_EXPERIMENT_CONFIGS = build_multi_core_configs()

SINGLE_CORE_ALL_ORDER: List[str] = [
    "baseline",
    "radix_perfect_pwc",
    "victima",
    "utopia",
    "potm",
    "vikram_both",
    "vikram_fetch",
    "vikram_ptb",
    "perfect",
    "virt_baseline",
    "virt_victima",
    "virt_utopia",
    "virt_potm",
    "virt_vikram_both",
]


def parse_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def supported_single_core_choices() -> List[str]:
    return ["all", "custom", *EXPERIMENT_CONFIGS.keys()]


def csv_choices(value_string: str) -> str:
    valid = set(supported_single_core_choices())
    values = parse_csv(value_string)
    for value in values:
        if value not in valid:
            raise argparse.ArgumentTypeError(
                f"Invalid choice: '{value}' (choose from {', '.join(sorted(valid))})"
            )
    return value_string


def multicore_csv_choices(value_string: str) -> str:
    valid = {"all", *MULTI_CORE_EXPERIMENT_CONFIGS.keys()}
    values = parse_csv(value_string)
    for value in values:
        if value not in valid:
            raise argparse.ArgumentTypeError(
                f"Invalid multicore choice: '{value}' (choose from {', '.join(sorted(valid))})"
            )
    return value_string


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a job file for Sniper single-core and multicore experiment runs."
    )
    parser.add_argument(
        "mount_path",
        help="Host path to mount at /app inside the container.",
    )
    parser.add_argument(
        "--experiment",
        type=csv_choices,
        default="all",
        help="Single-core experiments to emit. Use 'all' or a comma-separated subset.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Override config path. Required only when --experiment=custom.",
    )
    parser.add_argument(
        "--multicore",
        action="store_true",
        help="Also emit multicore experiment commands.",
    )
    parser.add_argument(
        "--multicore-experiment",
        type=multicore_csv_choices,
        default="all",
        help="Multicore experiments to emit when --multicore is enabled.",
    )
    parser.add_argument(
        "--results-dir",
        default="./results",
        help="Directory where per-workload outputs will be written.",
    )
    parser.add_argument(
        "--traces-dir",
        default="/app/traces/",
        help="Directory containing workload traces inside the container.",
    )
    parser.add_argument(
        "--jobfile",
        default="./baseline_jobfile.sh",
        help="Path to the generated jobfile script.",
    )
    parser.add_argument(
        "--joblist",
        default="./joblist.txt",
        help="Path to the generated joblist file.",
    )
    parser.add_argument(
        "--mode",
        choices=["native", "slurm"],
        default="native",
        help="Execution mode for the generated commands.",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional prefix for result directory names.",
    )
    parser.add_argument(
        "--excluded-nodes",
        default=None,
        help="Comma-separated node list to exclude when emitting Slurm commands.",
    )
    parser.add_argument(
        "--docker-image",
        default=DEFAULT_IMAGE,
        help="Docker image tag used to run the simulator.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of native jobs to launch before waiting.",
    )
    parser.add_argument(
        "--traces-mount",
        required=True,
        help="Host traces path to mount at --traces-dir inside the container.",
    )
    return parser


def q(value: str) -> str:
    return f'"{value}"'


def workload_label(trace_list: Sequence[str]) -> str:
    return "_".join(trace.split(".")[0] for trace in trace_list)


def make_docker_prefix(args: argparse.Namespace) -> str:
    return (
        f"docker run --rm -v {q(args.mount_path)}:/app "
        f"--mount type=bind,src={q(args.traces_mount)},target={args.traces_dir} "
        f"{q(args.docker_image)}"
    )


def resolve_single_core_experiments(args: argparse.Namespace) -> List[Tuple[str, str]]:
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    label_prefix = f"{args.label}_" if args.label else ""

    if args.experiment == "custom":
        if not args.config:
            raise SystemExit("--config is required when --experiment is 'custom'")
        label = args.label or "custom"
        return [(label, args.config)]

    keys: Iterable[str]
    if args.experiment == "all":
        keys = SINGLE_CORE_ALL_ORDER
    else:
        keys = parse_csv(args.experiment)

    resolved: List[Tuple[str, str]] = []
    for key in keys:
        config_info = EXPERIMENT_CONFIGS[key]
        resolved.append((f"{label_prefix}{config_info['label']}", args.config or config_info["config"]))
    return resolved


def resolve_multi_core_experiments(args: argparse.Namespace) -> List[Tuple[str, str, str]]:
    if not args.multicore:
        return []

    keys = (
        sorted(MULTI_CORE_EXPERIMENT_CONFIGS.keys())
        if args.multicore_experiment == "all"
        else parse_csv(args.multicore_experiment)
    )

    resolved: List[Tuple[str, str, str]] = []
    for key in keys:
        config_info = MULTI_CORE_EXPERIMENT_CONFIGS[key]
        cores = key.split("core", 1)[0]
        resolved.append((cores, config_info["label"], config_info["config"]))
    return resolved


def maybe_wrap_slurm(command: str, job_label: str, output_dir: Path, args: argparse.Namespace) -> str:
    if args.mode != "slurm":
        return command

    slurm_directives = [
        "sbatch",
        f"-J {job_label}",
        f"--output={output_dir}.out",
        f"--error={output_dir}.err",
    ]
    if args.excluded_nodes:
        slurm_directives.insert(1, f"--exclude={args.excluded_nodes}")

    return " ".join(slurm_directives) + ' docker_wrapper.sh "' + command + '"'


def build_single_core_commands(args: argparse.Namespace, docker_prefix: str) -> List[Tuple[str, str]]:
    commands: List[Tuple[str, str]] = []

    for experiment_label, config_path in resolve_single_core_experiments(args):
        experiment_root = Path(args.results_dir) / experiment_label
        experiment_root.mkdir(parents=True, exist_ok=True)

        for trace_name, trace in TRACES:
            output_dir = experiment_root / trace_name
            output_dir.mkdir(parents=True, exist_ok=True)

            base_command = (
                f"{docker_prefix} {SNIPER_COMMAND} "
                f"-d /app/{output_dir} "
                f"-c {config_path} "
                f"--traces={os.path.join(args.traces_dir, trace)}"
            )
            job_label = f"{experiment_label}_{trace_name}"
            commands.append((maybe_wrap_slurm(base_command, job_label, output_dir, args), job_label))

    return commands


def build_multi_core_commands(args: argparse.Namespace, docker_prefix: str) -> List[Tuple[str, str]]:
    commands: List[Tuple[str, str]] = []

    for cores, experiment_label, config_path in resolve_multi_core_experiments(args):
        experiment_root = Path(args.results_dir) / f"{cores}core" / experiment_label
        experiment_root.mkdir(parents=True, exist_ok=True)

        for trace_list in MULTICORE_WORKLOADS[cores]:
            trace_name = workload_label(trace_list)
            output_dir = experiment_root / trace_name
            output_dir.mkdir(parents=True, exist_ok=True)

            traces_arg = ",".join(os.path.join(args.traces_dir, trace) for trace in trace_list)
            base_command = (
                f"{docker_prefix} {SNIPER_COMMAND} "
                f"-d /app/{output_dir} "
                f"-c {config_path} "
                f"--traces={traces_arg}"
            )
            job_label = f"{experiment_label}_{trace_name}"
            commands.append((maybe_wrap_slurm(base_command, job_label, output_dir, args), job_label))

    return commands


def build_commands(args: argparse.Namespace) -> List[Tuple[str, str]]:
    docker_prefix = make_docker_prefix(args)
    commands = build_single_core_commands(args, docker_prefix)
    commands.extend(build_multi_core_commands(args, docker_prefix))
    return commands


def write_jobfile(args: argparse.Namespace, commands: List[Tuple[str, str]]) -> None:
    jobfile_path = Path(args.jobfile)
    jobfile_path.parent.mkdir(parents=True, exist_ok=True)

    joblist_path = Path(args.joblist)
    joblist_path.parent.mkdir(parents=True, exist_ok=True)

    with open(joblist_path, "w", encoding="utf-8") as joblist:
        for command, job_label in commands:
            joblist.write(f"LABEL={job_label}\n")
            joblist.write(f"CMD={command}\n\n")

    with open(jobfile_path, "w", encoding="utf-8") as jobfile:
        jobfile.write("#!/bin/bash\n\n")
        jobfile.write("set -e\n\n")

        for idx, (command, job_label) in enumerate(commands, start=1):
            if args.mode == "native":
                jobfile.write(f'echo "[START] {job_label}"\n')
                jobfile.write(f'({command}; echo "[DONE] {job_label}") &\n\n')
                if idx % args.batch_size == 0:
                    jobfile.write("wait\n")
                    jobfile.write(f'echo "Completed {idx} of {len(commands)} jobs"\n\n')
            else:
                jobfile.write(f'echo "Submitting {job_label}"\n')
                jobfile.write(f"{command}\n\n")

        if args.mode == "native":
            jobfile.write("wait\n")
            jobfile.write('echo "All jobs finished."\n')

    print(f"Wrote {len(commands)} commands to {jobfile_path} in {args.mode} mode.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    commands = build_commands(args)
    write_jobfile(args, commands)


if __name__ == "__main__":
    main()
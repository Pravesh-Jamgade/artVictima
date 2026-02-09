#!/usr/bin/env python3

"""Generate commands to run baseline or PTB experiments for all workloads."""

import argparse
import os
from pathlib import Path
from typing import Iterable, List, Tuple


TRACES = [
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

MULTICORE_WORKLOAD = {
    "8": [["cc.sift", "dlrm.sift", "gc.sift", "rnd.sift", "bfs.sift", "sssp.sift", "gen.sift", "pr.sift"]],
    "4": [["cc.sift", "dlrm.sift", "gc.sift", "rnd.sift"], ["bfs.sift", "sssp.sift", "gen.sift", "pr.sift"]],
    "2": [["cc.sift", "rnd.sift"], ["dlrm.sift", "rnd.sift"], ["gc.sift", "rnd.sift"], ["bfs.sift", "rnd.sift"]]
}

DEFAULT_IMAGE = "docker.io/kanell21/artifact_evaluation:victima"
SNIPER_COMMAND = "/app/sniper/run-sniper -s stop-by-icount:500000000 --genstats --power"

EXPERIMENT_CONFIGS = {
    "baseline": {
        "config": "/app/sniper/config/virtual_memory_configs/radix.cfg",
        "label": "baseline",
    },

    "radix_perfect_pwc": {
        "config": "/app/sniper/config/virtual_memory_configs/radix_perfect_pwc.cfg",
        "label": "radix_perfect_pwc",
    },

    "perfect": {
        "config": "/app/sniper/config/virtual_memory_configs/perfecttlb.cfg",
        "label": "perfect",
    },
    
    "vikram_both": {
        "config": "/app/sniper/config/virtual_memory_configs/vikram_both.cfg",
        "label": "vikram_both",
    },

    "vikram_fetch": {
        "config": "/app/sniper/config/virtual_memory_configs/vikram_fetch.cfg",
        "label": "vikram_fetch",
    },

    "vikram_ptb": {
        "config": "/app/sniper/config/virtual_memory_configs/vikram_ptb.cfg",
        "label": "vikram_ptb",
    },

    "victima": {
        "config": "/app/sniper/config/virtual_memory_configs/victima.cfg",
        "label": "victima",
    },

    "utopia": {
        "config": "/app/sniper/config/virtual_memory_configs/utopia.cfg",
        "label": "utopia",
    },

    "potm": {
        "config": "/app/sniper/config/virtual_memory_configs/potm.cfg",
        "label": "potm",
    },

    "tempo": {
        "config": "/app/sniper/config/virtual_memory_configs/tempo.cfg",
        "label": "tempo",
    },
    ##################################################

    "virt_baseline": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_radix.cfg",
        "label": "virt_baseline",
    },
    
    "virt_vikram_both": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_vikram_both.cfg",
        "label": "virt_vikram_both",
    },

    "virt_victima": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_victima.cfg",
        "label": "virt_victima",
    },

    "virt_utopia": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_utopia.cfg",
        "label": "virt_utopia",
    },

    "virt_potm": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_potm.cfg",
        "label": "virt_potm",
    },

    "virt_tempo": {
        "config": "/app/sniper/config/virtual_memory_configs/virt_tempo.cfg",
        "label": "virt_tempo",
    },
}

MULTI_CORE_EXPERIMENT_CONFIGS = {
     ###################################################################
    # 2 core Experiments
    ###################################################################

    "2core_baseline": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_radix.cfg",
        "label": "2core_baseline",
    },

    "2core_perfect": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_perfecttlb.cfg",
        "label": "2core_perfect",
    },
    
    "2core_vikram_both": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_vikram_both.cfg",
        "label": "2core_vikram_both",
    },

    "2core_victima": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_victima.cfg",
        "label": "2core_victima",
    },

    "2core_utopia": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_utopia.cfg",
        "label": "2core_utopia",
    },

    "2core_potm": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_potm.cfg",
        "label": "2core_potm",
    },

    "2core_tempo": {
        "config": "/app/sniper/config/virtual_memory_configs/2core_tempo.cfg",
        "label": "2core_tempo",
    },

     ###################################################################
    # 4 core Experiments
    ###################################################################

    "4core_baseline": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_radix.cfg",
        "label": "4core_baseline",
    },

    "4core_perfect": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_perfecttlb.cfg",
        "label": "4core_perfect",
    },
    
    "4core_vikram_both": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_vikram_both.cfg",
        "label": "4core_vikram_both",
    },

    "4core_victima": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_victima.cfg",
        "label": "4core_victima",
    },

    "4core_utopia": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_utopia.cfg",
        "label": "4core_utopia",
    },

    "4core_potm": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_potm.cfg",
        "label": "4core_potm",
    },

    "4core_tempo": {
        "config": "/app/sniper/config/virtual_memory_configs/4core_tempo.cfg",
        "label": "4core_tempo",
    },

     ###################################################################
    # 8 core Experiments
    ###################################################################

    "8core_baseline": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_radix.cfg",
        "label": "8core_baseline",
    },

    "8core_perfect": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_perfecttlb.cfg",
        "label": "8core_perfect",
    },
    
    "8core_vikram_both": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_vikram_both.cfg",
        "label": "8core_vikram_both",
    },

    "8core_victima": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_victima.cfg",
        "label": "8core_victima",
    },

    "8core_utopia": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_utopia.cfg",
        "label": "8core_utopia",
    },

    "8core_potm": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_potm.cfg",
        "label": "8core_potm",
    },

    "8core_tempo": {
        "config": "/app/sniper/config/virtual_memory_configs/8core_tempo.cfg",
        "label": "8core_tempo",
    },
}

# "baseline": {
#         "config": "/app/sniper/config/virtual_memory_configs_multicore/radix.cfg",
#         "label": "baseline",
#     },
#     "baseline-virtualized": {
#         "config": "/app/sniper/config/virtual_memory_configs_multicore/radix_virtual.cfg",
#         "label": "baseline_virtual",
#     },
#     "ptb": {
#         "config": "/app/sniper/config/virtual_memory_configs_multicore/ptb.cfg",
#         "label": "ptb",
#     },
#     "ptb-virtualized": {
#         "config": "/app/sniper/config/virtual_memory_configs_multicore/ptb_virtual.cfg",
#         "label": "ptb_virtual",
#     },



def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create a job file that launches all workloads across baseline and "
            "PTB configurations, with optional virtualized PTW variants."
        )
    )
    parser.add_argument(
        "mount_path",
        help=(
            "Host path to mount at /app inside the container (typically the "
            "repository root)."
        ),
    )
    parser.add_argument(
        "--experiment",
        type=csv_choices,
        help=(
            "Which experiment set to emit. 'all' writes baseline and PTB runs "
            "with and without virtualized PTW; 'custom' uses --config."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Sniper configuration file to use. Required when --experiment is "
            "'custom'; overrides the default config for other experiment types."
        ),
    )
    parser.add_argument(
        "--results-dir",
        default="./results",
        help="Directory where per-workload outputs will be written.",
    )
    parser.add_argument(
        "--traces-dir",
        default="/app/traces/",
        help="Directory containing the workload trace files inside the container.",
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
        help="Optional prefix for result directory names (defaults to experiment label).",
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
        help="Number of native jobs to launch before waiting for completion.",
    )

    parser.add_argument(
        "--traces-mount",
        help="Traces from host location $(--trace-mount) to be mounted at $(--trace-dir)",
    )
    return parser


def csv_choices(value_string):
    """
    Returns a function that validates comma-separated inputs against a list of choices.
    """
    choices = [
        "all",
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

        "tempo",
        "virt_tempo",
        
    ]

    values = [v.strip() for v in value_string.split(",")]
    for v in values:
        if v not in choices:
            # This integrates with argparse's error handling
            raise argparse.ArgumentTypeError(
                f"Invalid choice: '{v}' (choose from {', '.join(choices)})"
            )
    return value_string  # Returns a list of valid choices


def parse_string_experiments(value) -> List[str]:
    return [v.strip() for v in value.split(",")]


def resolve_experiments(args: argparse.Namespace) -> List[Tuple[str, str]]:
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    label_prefix = f"{args.label}_" if args.label else ""

    if args.experiment == "custom":
        if not args.config:
            raise SystemExit("--config is required when --experiment is 'custom'")
        label = args.label or "custom"
        return [(label, args.config)]

    if args.experiment == "all":
        keys: Iterable[str] = [
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
    else:
        keys = parse_string_experiments(args.experiment)

    resolved = []
    for key in keys:
        config_info = EXPERIMENT_CONFIGS[key]
        label = f"{label_prefix}{config_info['label']}"
        config_path = args.config or config_info["config"]
        resolved.append((label, config_path))
    return resolved

def resolve_multi_core_experiments(args: argparse.Namespace) -> List[Tuple[str, str, str]]:
    resolved = []
    keys = parse_string_experiments(args.experiment)
    print(keys)
    for key in keys:
       
        for config_name, config_info in MULTI_CORE_EXPERIMENT_CONFIGS.items():
            if key not in config_name:
                continue
            cores = config_name.split("core")[0]
            label = f"{config_info['label']}"
            config_path = args.config or config_info["config"]
            resolved.append((cores, label, config_path))
        return resolved

def q(value):
    return f'\"{value}\"'


def build_commands(args: argparse.Namespace) -> List[Tuple[str, str]]:
    docker_prefix = f"docker run --rm -v {q(args.mount_path)}:/app --mount type=bind,src={q(args.traces_mount)},target={args.traces_dir} {q(args.docker_image)} "

    commands: List[Tuple[str, str]] = []
    for experiment_label, config_path in resolve_experiments(args):
        experiment_root = Path(args.results_dir) / experiment_label
        experiment_root.mkdir(parents=True, exist_ok=True)

        for trace_name, trace in TRACES:
            output_dir = experiment_root / trace_name
            os.makedirs(output_dir, exist_ok=True)

            trace_command = f"--traces={os.path.join(args.traces_dir, trace)}"
            output_command = f"-d /app/{output_dir}"
            config_command = f"-c {config_path}"
            job_label = f"{experiment_label}_{trace_name}"

            base_command = (
                f"{docker_prefix} {SNIPER_COMMAND} "
                f"{output_command} {config_command} {trace_command}"
            )

            if args.mode == "slurm":
                slurm_directives = [
                    "sbatch",
                    f"-J {job_label}",
                    f"--output={output_dir}.out",
                    f"--error={output_dir}.err",
                ]
                if args.excluded_nodes:
                    slurm_directives.insert(1, f"--exclude={args.excluded_nodes}")

                command = (
                    " ".join(slurm_directives)
                    + ' docker_wrapper.sh "'
                    + base_command
                    + '"'
                )
            else:
                command = f"{base_command} > {output_dir}.out 2> {output_dir}.err"

            commands.append((command, job_label))

    multicore_jobs = resolve_multi_core_experiments(args)
    if not multicore_jobs:
        return commands
    for cores, experiment_label, config_path in multicore_jobs:
        experiment_root = Path(args.results_dir) / f"{cores}core" / experiment_label
        experiment_root.mkdir(parents=True, exist_ok=True)
        trace_group = MULTICORE_WORKLOAD[cores]

        for trace_list in trace_group:
            trace_name = "_".join([t.split(".")[0] for t in trace_list])
            output_dir = experiment_root / trace_name
            os.makedirs(output_dir, exist_ok=True)

            trace_command = f"--traces={','.join([os.path.join(args.traces_dir, t) for t in trace_list])}"
            output_command = f"-d /app/{output_dir}"
            config_command = f"-c {config_path}"
            job_label = f"{experiment_label}_{trace_name}"

            base_command = (
                f"{docker_prefix} {SNIPER_COMMAND} "
                f"{output_command} {config_command} {trace_command}"
            )

            if args.mode == "slurm":
                slurm_directives = [
                    "sbatch",
                    f"-J {job_label}",
                    f"--output={output_dir}.out",
                    f"--error={output_dir}.err",
                ]
                if args.excluded_nodes:
                    slurm_directives.insert(1, f"--exclude={args.excluded_nodes}")

                command = (
                    " ".join(slurm_directives)
                    + ' docker_wrapper.sh "'
                    + base_command
                    + '"'
                )
            else:
                command = f"{base_command} > {output_dir}.out 2> {output_dir}.err"

            commands.append((command, job_label))

    return commands


def write_jobfile(args: argparse.Namespace, commands: List[Tuple[str, str]]):
    jobfile_path = Path(args.jobfile)
    jobfile_path.parent.mkdir(parents=True, exist_ok=True)

    joblistfile_path = Path(args.joblist)

    with open(joblistfile_path, "w", encoding="utf-8") as jobfile:
        for cmd, job_label in commands:
            jobfile.write(f"LABEL={job_label}\n")
            jobfile.write(f"CMD={cmd}\n")
            jobfile.write("\n")

    with open(jobfile_path, "w", encoding="utf-8") as jobfile:
        jobfile.write("#!/bin/bash\n\n")
        jobfile.write("set -e\n\n")

        for idx, (command, job_label) in enumerate(commands, start=1):
            if args.mode == "native":
                jobfile.write(f"echo \"[START] {job_label}\"\n")
                jobfile.write(f"({command}; echo \"[DONE] {job_label}\") &\n\n")

                if idx % args.batch_size == 0:
                    jobfile.write("wait\n")
                    jobfile.write(
                        f"echo \"Completed {idx} of {len(commands)} jobs\"\n\n"
                    )
            else:
                jobfile.write(f"echo \"Submitting {job_label}\"\n")
                jobfile.write(f"{command}\n\n")

        if args.mode == "native":
            jobfile.write("wait\n")
            jobfile.write("echo \"All jobs finished.\"\n")

    print(f"Wrote {len(commands)} commands to {jobfile_path} in {args.mode} mode.")


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = build_commands(args)
    write_jobfile(args, commands)


if __name__ == "__main__":
    main()

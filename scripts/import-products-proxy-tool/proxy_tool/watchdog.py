from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from .system import (
    atomic_json,
    cleanup_pktmon,
    pid_alive,
    terminate_pid,
)
from .windivert_native import KillSwitch


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--gate-pid", type=int, required=True)
    parser.add_argument("--proxy-ips", required=True)
    parser.add_argument("--proxy-port", type=int, required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument(
        "--gate-death-grace",
        type=float,
        default=8.0,
    )

    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    ready_file = state_dir / "watchdog.ready.json"
    stop_file = state_dir / "stop.requested"
    failure_file = state_dir / "watchdog.failure.json"
    stopped_file = state_dir / "watchdog.stopped.json"

    proxy_ips = [
        value.strip()
        for value in args.proxy_ips.split(",")
        if value.strip()
    ]

    kill_switch = KillSwitch(
        gate_pid=args.gate_pid,
        proxy_ips=proxy_ips,
        proxy_port=args.proxy_port,
    )

    try:
        kill_switch.open()

        atomic_json(
            ready_file,
            {
                "pid": os.getpid(),
                "ready": True,
                "gate_pid": args.gate_pid,
            },
        )

        gate_dead_since = None

        while True:
            if stop_file.exists():
                break

            if not pid_alive(args.parent_pid):
                break

            if not pid_alive(args.gate_pid):
                if gate_dead_since is None:
                    gate_dead_since = time.monotonic()

                    atomic_json(
                        failure_file,
                        {
                            "reason": "gate_process_died",
                            "gate_pid": args.gate_pid,
                            "parent_pid": args.parent_pid,
                        },
                    )

                elif (
                    time.monotonic() - gate_dead_since
                    >= args.gate_death_grace
                ):
                    # Keep the kill-switch active until the controller
                    # has been killed, then finally release network.
                    terminate_pid(args.parent_pid)
                    break
            else:
                gate_dead_since = None

            time.sleep(0.25)

    finally:
        try:
            kill_switch.close()
        finally:
            cleanup_pktmon()

            atomic_json(
                stopped_file,
                {
                    "pid": os.getpid(),
                    "stopped": True,
                    "time": time.time(),
                },
            )


if __name__ == "__main__":
    main()
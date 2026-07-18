"""Demo 01: Getting Started — Deploy (create harness)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import banner, step_header, success, info, config_val, error, done
from shared.stack_config import get_config
from shared.harness_helpers import (
    create_harness,
    get_harness_status,
    save_config,
    load_config,
)

HARNESS_NAME = "m07_demo01_getting_started"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")


def main():
    banner("Demo 01: Getting Started — Deploy")

    # ── Step 1: Check existing config ─────────────────────────────────────────
    step_header(1, 3, "Check existing deployment")

    if os.path.exists(CONFIG_FILE):
        config = load_config(CONFIG_FILE)
        status = get_harness_status(config["harness_id"], config["region"])
        if status == "READY":
            success(f"Harness already exists and is READY")
            config_val("harness_id", config["harness_id"])
            config_val("harness_arn", config["harness_arn"])
            done("python invoke.py")
            return
        else:
            info(f"Existing harness status: {status} — recreating...")

    # ── Step 2: Get stack config ──────────────────────────────────────────────
    step_header(2, 3, "Read CloudFormation stack config")

    stack = get_config()
    config_val("region", stack["region"])
    config_val("account_id", stack["account_id"])
    config_val("harness_role_arn", stack["harness_role_arn"])

    # ── Step 3: Create harness ────────────────────────────────────────────────
    step_header(3, 3, "Create harness")

    result = create_harness(
        name=HARNESS_NAME,
        role_arn=stack["harness_role_arn"],
        region=stack["region"],
    )

    config = {
        "harness_id": result["harness_id"],
        "harness_arn": result["harness_arn"],
        "region": stack["region"],
        "harness_name": HARNESS_NAME,
    }
    save_config(config, CONFIG_FILE)

    config_val("harness_id", result["harness_id"])
    config_val("harness_arn", result["harness_arn"])
    done("python invoke.py")


if __name__ == "__main__":
    main()

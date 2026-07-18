"""Demo 02: Execute Command — Cleanup (delete harness)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import banner, step_header, success, info, config_val, done
from shared.harness_helpers import load_config, delete_harness

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")


def main():
    banner("Demo 02: Execute Command — Cleanup")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 2, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_id", config["harness_id"])
    config_val("region", config["region"])

    # ── Step 2: Delete harness ────────────────────────────────────────────────
    step_header(2, 2, "Delete harness")

    delete_harness(config["harness_id"], config["region"])

    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        info("Config file removed")

    done()


if __name__ == "__main__":
    main()

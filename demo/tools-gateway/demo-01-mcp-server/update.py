"""
Update agent/server code without recreating the runtime.

Uses update_agent_runtime() to push new code to the existing runtime.
The endpoint stays the same — no downtime, no new ARN.

Usage:
    # Edit the server/agent code, then:
    python update.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.update_helpers import update_runtime
from shared.colors import banner, success, info, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Updating Code (in-place)")
    info("Rebuilding arm64 package...")
    runtime_id = update_runtime(agent_files=["mcp_server.py"])
    success(f"Runtime updated: {runtime_id}")
    info("New code is live — no new endpoint or ARN needed")
    done("python invoke.py")


if __name__ == "__main__":
    main()

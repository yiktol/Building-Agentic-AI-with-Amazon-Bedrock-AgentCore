"""
Demo 5: Streaming Invocation — watch tokens arrive in real time.

Compares:
  Part 1: Non-streaming (waits for full response)
  Part 2: Streaming (tokens appear incrementally via SSE)

The key difference is ONLY the `accept` header — agent code is unchanged.

Usage:
    python invoke.py
    python invoke.py "Explain quantum computing in detail"
"""

import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, config_val, prompt_display, done,
    GREEN, YELLOW, RESET, BOLD, WHITE, MAGENTA,
)

import boto3


def load_config() -> dict:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open("runtime_config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        from shared.colors import error
        error("runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)


def invoke_blocking(client, arn: str, prompt: str) -> tuple:
    """Non-streaming invocation — blocks until complete."""
    start = time.time()
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    body = response["response"].read().decode("utf-8")
    elapsed = time.time() - start
    return body, elapsed


def invoke_streaming(client, arn: str, prompt: str) -> float:
    """Streaming invocation — displays tokens as they arrive."""
    start = time.time()
    first_token_time = None

    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="text/event-stream",
    )

    stream = response["response"]
    print(f"  {GREEN}", end="", flush=True)

    found_sse = False
    byte_buffer = b""

    try:
        for chunk in stream.iter_chunks():
            if isinstance(chunk, tuple):
                chunk = chunk[0]
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")

            byte_buffer += chunk

            # Decode only complete UTF-8 sequences
            try:
                text = byte_buffer.decode("utf-8")
                byte_buffer = b""
            except UnicodeDecodeError:
                # Incomplete multi-byte char at the end — wait for more data
                continue

            # Process complete lines
            while "\n" in text:
                line, text = text.split("\n", 1)
                line = line.strip()
                if line.startswith("data:"):
                    if first_token_time is None:
                        first_token_time = time.time() - start
                    data = line[5:].strip()
                    if data:
                        print(data, end="", flush=True)
                        found_sse = True

            # Put remaining partial line back as bytes for next iteration
            if text:
                byte_buffer = text.encode("utf-8")

    except AttributeError:
        # Fallback: iter_chunks not available — read all, display word-by-word
        all_bytes = byte_buffer + stream.read()
        decoded = all_bytes.decode("utf-8", errors="replace")
        for line in decoded.splitlines():
            if line.startswith("data:"):
                if first_token_time is None:
                    first_token_time = time.time() - start
                data = line[5:].strip()
                if data:
                    words = data.split(" ")
                    for i, word in enumerate(words):
                        print(word, end=" " if i < len(words) - 1 else "", flush=True)
                        time.sleep(0.03)
                    found_sse = True

    # Process any remaining bytes in buffer
    if byte_buffer:
        remaining = byte_buffer.decode("utf-8", errors="replace").strip()
        if remaining.startswith("data:"):
            data = remaining[5:].strip()
            if data:
                if first_token_time is None:
                    first_token_time = time.time() - start
                print(data, end="", flush=True)
                found_sse = True

    if not found_sse:
        # Response wasn't SSE — display word-by-word to simulate streaming
        if first_token_time is None:
            first_token_time = time.time() - start
        try:
            body = (byte_buffer + stream.read()).decode("utf-8", errors="replace")
        except Exception:
            body = byte_buffer.decode("utf-8", errors="replace")
        words = body[:500].split(" ")
        for i, word in enumerate(words):
            print(word, end=" " if i < len(words) - 1 else "", flush=True)
            time.sleep(0.03)

    print(f"{RESET}")
    total_time = time.time() - start
    return first_token_time or total_time


def main():
    config = load_config()
    arn = config["runtime_arn"]
    region = config["region"]
    client = boto3.client("bedrock-agentcore", region_name=region)

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Explain how neural networks learn through backpropagation. Include details about gradient descent, loss functions, and weight updates."

    banner("Demo 5: Streaming vs Non-Streaming Responses")
    config_val("Runtime", arn)

    # Part 1: Non-streaming
    section("Part 1: Non-streaming (blocking)")
    info("accept: application/json")
    prompt_display(prompt[:80] + "...")
    info("Waiting for complete response...")

    body, elapsed = invoke_blocking(client, arn, prompt)
    print(f"  {MAGENTA}Response ({elapsed:.1f}s total wait):{RESET}")
    print(f"  {body[:200]}...\n")

    # Part 2: Streaming
    section("Part 2: Streaming (SSE)")
    info("accept: text/event-stream")
    prompt_display(prompt[:80] + "...")
    info("Streaming tokens in real time:\n")

    first_token = invoke_streaming(client, arn, prompt)

    print(f"\n  {YELLOW}First token:{RESET} {WHITE}{BOLD}{first_token:.2f}s{RESET} vs {elapsed:.1f}s total blocking")

    done()
    info("Key takeaway: Streaming is a CLIENT-SIDE choice")
    info("  • Same agent code — no changes needed")
    info("  • Only difference: accept='text/event-stream'")
    print()


if __name__ == "__main__":
    main()

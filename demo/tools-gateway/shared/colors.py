"""
ANSI color utilities for demo CLI output.

Provides consistent color-coded output across all demo scripts.
"""

# ── ANSI Codes ────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

CYAN = "\033[96m"      # Step headers
GREEN = "\033[92m"     # Success
YELLOW = "\033[93m"    # Info / in-progress
MAGENTA = "\033[95m"   # Config values
BLUE = "\033[94m"      # Banners
WHITE = "\033[97m"     # Emphasis
RED = "\033[91m"       # Errors


# ── Output Helpers ────────────────────────────────────────────────────────────

def banner(title: str):
    """Print a blue bold banner."""
    print(f"\n{BLUE}{BOLD}{'═' * 60}{RESET}")
    print(f"{BLUE}{BOLD}  {title}{RESET}")
    print(f"{BLUE}{BOLD}{'═' * 60}{RESET}")


def step_header(num: int, total: int, title: str):
    """Print a cyan boxed step header."""
    print(f"\n{CYAN}{BOLD}┌{'─' * 56}┐{RESET}")
    print(f"{CYAN}{BOLD}│  Step {num}/{total}: {title:<46}│{RESET}")
    print(f"{CYAN}{BOLD}└{'─' * 56}┘{RESET}")


def section(title: str):
    """Print a cyan boxed section header (no step number)."""
    print(f"\n{CYAN}{BOLD}┌{'─' * 56}┐{RESET}")
    print(f"{CYAN}{BOLD}│  {title:<54}│{RESET}")
    print(f"{CYAN}{BOLD}└{'─' * 56}┘{RESET}")


def success(msg: str):
    """Print a green success message."""
    print(f"  {GREEN}✓ {msg}{RESET}")


def info(msg: str):
    """Print a yellow info/in-progress message."""
    print(f"  {YELLOW}→ {msg}{RESET}")


def error(msg: str):
    """Print a red error message."""
    print(f"  {RED}✗ {msg}{RESET}")


def config_val(key: str, value: str):
    """Print a key-value pair with dim key and magenta value."""
    print(f"  {DIM}{key}:{RESET} {MAGENTA}{value}{RESET}")


def prompt_display(prompt: str):
    """Print a prompt being sent."""
    print(f"  {WHITE}{BOLD}→ Prompt:{RESET} {prompt}")


def response_display(response: str, max_len: int = 300):
    """Print an agent response."""
    text = response[:max_len] + ("..." if len(response) > max_len else "")
    print(f"  {GREEN}← Response:{RESET} {text}")


def done(next_cmd: str = None):
    """Print completion banner with optional next command."""
    print(f"\n{GREEN}{BOLD}{'═' * 60}{RESET}")
    print(f"{GREEN}{BOLD}  ✓ Done!{RESET}")
    print(f"{GREEN}{BOLD}{'═' * 60}{RESET}")
    if next_cmd:
        print(f"\n  {WHITE}{BOLD}Next:{RESET} {next_cmd}\n")

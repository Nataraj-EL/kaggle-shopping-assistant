import json
import re
import sys

BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",  # rm -rf /
    r"rm\s+-r\s+/",  # rm -r /
    r"rm\s+--recursive\s+/",  # rm --recursive /
    r"dd\s+if=.*of=/dev/sda",  # destructive dd
    r"mkfs\..*",  # filesystem creation
]


def main():
    raw_input = sys.stdin.read()

    # Try parsing as JSON first
    command_str = None
    try:
        data = json.loads(raw_input)
        # Check standard ADK/framework tool invocation formats
        if isinstance(data, dict):
            args = data.get("arguments") or data.get("args") or data
            if isinstance(args, dict):
                command_str = (
                    args.get("CommandLine") or args.get("command") or args.get("cmd")
                )
            elif isinstance(args, str):
                command_str = args
    except json.JSONDecodeError:
        # Fall back to raw string analysis
        command_str = raw_input

    if not command_str:
        command_str = raw_input

    command_clean = command_str.strip()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command_clean):
            print(
                f"SECURITY BLOCK: The command '{command_clean}' matches blocked pattern '{pattern}' and has been terminated.",
                file=sys.stderr,
            )
            sys.exit(2)  # Exit with non-zero code to block execution

    sys.exit(0)


if __name__ == "__main__":
    main()

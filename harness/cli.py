"""
harness/cli.py — Command-Line Interface for TalentOps Automation Harness
========================================================================

Allows issuing commands and controlling connected applications directly from terminal.
Usage:
    python -m harness.cli "status"
    python -m harness.cli "check_inbox 5"
    python -m harness.cli "check_calls 5"
    python -m harness.cli "outreach 'John Doe' john@corp.com +12065550199 'Amazon'"
    python -m harness.cli "focus teams"
"""

import sys
import json
from harness.command_engine import command_engine


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m harness.cli <command>")
        print("\nAvailable commands:")
        for cmd, desc in command_engine.get_help_topics().items():
            print(f"  {cmd:<30} {desc}")
        sys.exit(0)

    cmd_line = " ".join(sys.argv[1:])
    result = command_engine.execute(cmd_line)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

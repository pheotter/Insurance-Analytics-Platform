"""Administrative commands for the actuarial workflow schema."""

from __future__ import annotations

import argparse

from .snowflake_repository import SnowflakeWorkflowRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init-schema",))
    args = parser.parse_args()
    if args.command == "init-schema":
        SnowflakeWorkflowRepository.from_environment().initialize_schema()
        print("Actuarial workflow tables are ready")


if __name__ == "__main__":
    main()

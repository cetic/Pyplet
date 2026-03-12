import argparse
import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

project_dir = Path.cwd() / "apps"


def create_project(project_name: str) -> None:
    """
    Create a new project directory under ./apps/project_name and copy
    template_client.py, template_server.py, and config.py from ../apps/examples
    into it.

    Args:
        project_name (str): The name of the project to create.
    """
    # Validate project name for Python importability
    if not project_name.isidentifier():
        logger.error(
            "%s is not a valid Python's module name."
            "Use only letters, numbers and underscores, "
            "and dont start with a number." % project_name
        )
        sys.exit(1)
    cwd = Path.cwd()
    pyplet_dir = Path(__file__).resolve().parent.parent
    template_dir = pyplet_dir.parent / "apps" / "template"

    # Sources
    src_client = template_dir / "template_client.py"
    src_server = template_dir / "template_server.py"
    src_config = template_dir / "config.py"

    # Create apps dir if it doesn't exist
    apps_dir = cwd / "apps"

    if not apps_dir.exists():
        logger.info("Creating './apps' directory")
        apps_dir.mkdir(parents=True, exist_ok=True)

    else:
        logger.info("Apps directory './apps/' already exists, skipping copy")

    # Create project dir if it doesn't exist
    project_dir = apps_dir / project_name
    if project_dir.exists():
        logger.warning("The directory '%s' already exists.", project_name)
        sys.exit(1)

    project_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Project '%s' created at %s", project_name, project_dir)

    # Copy files
    shutil.copyfile(src_client, project_dir / f"{project_name}_client.py")
    shutil.copyfile(src_server, project_dir / f"{project_name}_server.py")
    shutil.copyfile(src_config, project_dir / "config.py")

    logger.info("[OK] Files copied: client.py, server.py, config.py")


def script_main() -> None:
    """Run the Pyplet server CLI script."""
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    main()


def main() -> None:
    from pyplet.server import config

    parser = argparse.ArgumentParser(description="Pyplet project initializer")
    subparsers = parser.add_subparsers(dest="command")

    # init command
    parser_init = subparsers.add_parser(
        "init",
        help="Create a new project directory with client.py, "
        "server.py and config.py under ./apps/",
    )

    parser_init.add_argument(
        "project_name",
        help="Name of the project directory to create under ./apps/",
    )

    # start command
    parser_start = subparsers.add_parser(
        "start", aliases=["run", "server"], help="Launch pyplet.server.main()"
    )

    for name in config.params:
        parser_start.add_argument(
            f"--{name.replace('_', '-')}",
            required=False,
            default=getattr(config, name),
        )

    args = parser.parse_args()

    # If no command is provided, print help and exit
    if args.command is None:
        parser.print_help()
        return

    if args.command == "init":
        create_project(args.project_name)

    elif args.command in ("start", "run", "server"):
        if not project_dir.exists():
            logger.error("No project found. Run 'pyplet init' first.")
            return

        for name in config.params:
            value = getattr(args, name, ...)
            if value is not ...:
                setattr(config, name, value)

        start_server()

    else:
        parser.print_help()


def start_server() -> None:
    """
    Import pyplet.server.__init__ and run its main() function.
    """
    from .web import astart

    try:
        asyncio.run(astart())

    except KeyboardInterrupt:
        logger.info("Server killed by the user.")
        sys.exit(0)


if __name__ == "__main__":
    main()

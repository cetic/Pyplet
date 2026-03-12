import argparse
import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pyplet.cli")

projects_dir = Path.cwd() / "apps"


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

    # Verify template directory exists
    if not template_dir.exists():
        logger.error(f"Template directory not found: {template_dir}")
        sys.exit(1)

    # Sources
    src_client = template_dir / "template_client.py"
    src_server = template_dir / "template_server.py"

    # Create apps and project dir if they don't exist
    project_dir = cwd / "apps" / project_name

    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Project '{}' created at {}".format(project_name, project_dir)
        )

    # Copy files
    dest_client = project_dir / f"{project_name}_client.py"
    dest_server = project_dir / f"{project_name}_server.py"

    # Verify template directory exists
    if dest_client.exists() or dest_server.exists():
        logger.error(
            "At least one of %s and %s already exists",
            dest_client,
            dest_server,
        )
        sys.exit(1)

    shutil.copyfile(src_client, dest_client)
    shutil.copyfile(src_server, dest_server)

    logger.info(f"Files copied: {dest_client.name}, {dest_server.name}")
    logger.info(
        "Project '%s' is ready! Start the server with: pyplet start",
        project_name,
    )


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


def start_server():
    """
    Start the Pyplet server.
    """
    from ._server import astart

    logger.info("Starting Pyplet server...")

    try:
        asyncio.run(astart())

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)

    except Exception as error:
        logger.error("Server error: %s", error, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

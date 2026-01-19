import os
import sys
import argparse
import shutil
from pathlib import Path
import importlib
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pyplet.cli")


def create_project(project_name: str):
    """
    Create a new project directory under ./apps/project_name and copy
    template_client.py and template_server.py from the template directory.
    """
    # Validate project name for Python importability
    if not project_name.isidentifier():
        logger.error(
            f"'{project_name}' is not a valid Python module name. "
            "Use only letters, numbers and underscores, "
            "and don't start with a number."
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
        logger.info(f"Project '{project_name}' created at {project_dir}")

    # Copy files
    dest_client = project_dir / f"{project_name}_client.py"
    dest_server = project_dir / f"{project_name}_server.py"

    # Verify template directory exists
    if dest_client.exists() or dest_server.exists():
        logger.error(f"At least one of {dest_client} and {dest_server} already exists")
        sys.exit(1)

    shutil.copyfile(src_client, dest_client)
    shutil.copyfile(src_server, dest_server)

    logger.info(f"Files copied: {dest_client.name}, {dest_server.name}")
    logger.info(
        f"Project '{project_name}' is ready! Start the server with: pyplet start"
    )


def script_main():
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    main()


def main():
    from pyplet.server import config

    parser = argparse.ArgumentParser(description="Pyplet project initializer")
    subparsers = parser.add_subparsers(dest="command")

    # init command
    parser_init = subparsers.add_parser(
        "init",
        help="Create a new project directory with client and server files under ./apps/",
    )
    parser_init.add_argument(
        "project_name", help="Name of the project directory to create under ./apps/"
    )

    # start command
    parser_start = subparsers.add_parser("start", help="Launch pyplet.server.main()")
    for name in config.__all__:
        parser_start.add_argument(
            f'--{name.replace("_", "-")}', required=False, default=getattr(config, name)
        )

    args = parser.parse_args()

    if args.command == "init":
        create_project(args.project_name)
    elif args.command == "start":
        for name in config.__all__:
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
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

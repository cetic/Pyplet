import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path


def create_project(project_name: str):
    """
    Create a new project directory under ./apps/project_name and copy
    template_client.py, template_server.py, and config.py from ../apps/examples
    into it.
    """
    # Validate project name for Python importability
    if not project_name.isidentifier():
        print(
            f"[ERROR] '{project_name}' is not a valid Python's module name . "
            "Use only letters, numbers and underscores, "
            "and dont start with a number."
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
        print("[INFO] Creating './apps' directory")
        apps_dir.mkdir(parents=True, exist_ok=True)
    else:
        print("[INFO] Apps directory './apps/' already exists, skipping copy")

    # Create project dir if it doesnt exist
    project_dir = apps_dir / project_name
    if project_dir.exists():
        print(f"[ERROR] The directory '{project_dir}' already exists.")
        sys.exit(1)
    project_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Project '{project_name}' created at {project_dir}")

    # Copy files
    shutil.copyfile(src_client, project_dir / f"{project_name}_client.py")
    shutil.copyfile(src_server, project_dir / f"{project_name}_server.py")
    shutil.copyfile(src_config, project_dir / "config.py")

    print("[OK] Files copied: client.py, server.py, config.py")


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
        help="Create a new project directory with client.py, server.py and config.py under ./apps/",
    )
    parser_init.add_argument(
        "project_name",
        help="Name of the project directory to create under ./apps/",
    )

    # start command
    parser_start = subparsers.add_parser(
        "start", help="Launch pyplet.server.main()"
    )
    for name in config.__all__:
        parser_start.add_argument(
            f"--{name.replace('_', '-')}",
            required=False,
            default=getattr(config, name),
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
    Import pyplet.server.__init__ and run its main() function.
    """
    from .web import astart

    asyncio.run(astart())


if __name__ == "__main__":
    main()

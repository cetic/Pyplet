import argparse
import shutil
from pathlib import Path
import sys
import importlib


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
    script_dir = Path(__file__).resolve().parent
    template_dir = script_dir.parent / "apps" / "template"

    # Sources
    src_client = template_dir / "template_client.py"
    src_server = template_dir / "template_server.py"
    src_config = template_dir / "config.py"
    src_global_config = script_dir.parent / "apps" / "config.py"

    # Create apps dir if it doesn't exist
    apps_dir = cwd / "apps"
    if not apps_dir.exists():
        print(f"[INFO] Creating './apps' directory")
        apps_dir.mkdir(parents=True, exist_ok=True)
    else:
        print(f"[INFO] Apps directory './apps/' already exists, skipping copy")

    # Copy global config.py only if it does not exist
    global_config_dest = apps_dir / "config.py"
    if not global_config_dest.exists():
        shutil.copyfile(src_global_config, global_config_dest)
        print(f"[OK] Global config copied to './apps/config.py'")
    else:
        print(f"[INFO] Global config './apps/config.py' already exists, skipping copy")

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

    print(f"[OK] Files copied: client.py, server.py, config.py")


def start_server():
    """
    Import pyplet.server.__init__ and run its main() function.
    """
    try:
        server_module = importlib.import_module("pyplet.server")
    except ModuleNotFoundError:
        print("[ERROR] pyplet.server module not found. Is pyplet installed?")
        sys.exit(1)

    print("[OK] Starting pyplet server...")
    server_module.main()


def main():
    parser = argparse.ArgumentParser(description="Pyplet project initializer")
    subparsers = parser.add_subparsers(dest="command")

    # init command
    parser_init = subparsers.add_parser(
        "init",
        help="Create a new project directory with client.py, server.py and config.py under ./apps/",
    )
    parser_init.add_argument(
        "project_name", help="Name of the project directory to create under ./apps/"
    )

    # start command
    subparsers.add_parser("start", help="Launch pyplet.server.main()")

    args = parser.parse_args()

    if args.command == "init":
        create_project(args.project_name)
    elif args.command == "start":
        start_server()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

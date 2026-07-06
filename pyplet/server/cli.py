import argparse
import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

from .config import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pyplet.cli")


def create_project(project_name: str, tutorial: bool = False) -> None:
    """
    Create a new project directory under ./apps/project_name and copy
    template_client.py, template_server.py, and config.py from ../apps/examples
    into it.

    Args:
        project_name (str): The name of the project to create.
        tutorial (bool): Whether to create a tutorial project.
    """
    # Validate project name for Python importability
    if not project_name.isidentifier():
        logger.error(
            "%s is not a valid Python's module name. "
            "Use only letters, numbers and underscores, "
            "and don't start with a number." % project_name
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

    if tutorial:
        src_client = template_dir / "tutorial_client.py"
        src_server = template_dir / "tutorial_server.py"

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


# Entry point when run as `pyplet [...]`
def script_main() -> None:
    """Run the Pyplet server CLI script."""
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    main()


def main() -> None:
    from pyplet.server.config import config

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
        "start",
        # aliases=["run", "server"],
        help="Launch pyplet.server.main()",
    )

    # Tutorial
    subparsers.add_parser(
        "tutorial",
        help="Launch the Pyplet tutorial server with a sample project",
    )

    for name in config.params:
        param_obj = getattr(type(config), name)

        parser_start.add_argument(
            f"--{name.replace('_', '-')}",
            required=False,
            help=f"{param_obj.description} [Env: {param_obj.env_var}]",
            default=os.environ.get(param_obj.env_var, argparse.SUPPRESS),
            type=param_obj.type_cast,
        )

    args = parser.parse_args()

    # If no command is provided, print help and exit
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        create_project(args.project_name)

    elif args.command in ("start"):  # , "run", "server"):
        projects_dir = Path(config.apps)

        # If path is relative, make it absolute
        if not projects_dir.is_absolute():
            projects_dir = Path.cwd() / projects_dir

        # If path doesn't exist, print error and exit
        if not projects_dir.exists():
            logger.error(
                "No projects directory found in the current directory.\n"
                "Run 'pyplet init <project_name>' first or move to the "
                "projects directory."
            )
            sys.exit(2)

        for name in config.params:
            value = getattr(args, name, ...)
            if value is not ...:
                setattr(config, name, value)

        start_server()

    elif args.command == "tutorial":
        # The tutorial command launches a quick start example that
        # helps to explain the basics of Pyplet. How to create a project,
        # how to define a client and a server, and how to run them.
        # Todo: implement the tutorial command
        print(
            "Welcome to the Pyplet tutorial! This command will launch"
            " a sample project that demonstrates the basics of Pyplet."
            "\n\nTo get started, run the following command: "
            "pyplet init tutorial"
        )

        try:
            while True:
                prompt_symbol = sys.platform == "win32" and "> " or "$ "

                # Detect root user and change prompt symbol to #
                if os.name != "nt" and os.geteuid() == 0:
                    prompt_symbol = "# "

                tutorial_command = input(prompt_symbol)
                if tutorial_command.lower() in ("exit", "quit"):
                    print("Exiting tutorial. Goodbye!")
                    break

                elif tutorial_command != "pyplet init tutorial":
                    print(
                        "Invalid command. Please run 'pyplet init tutorial' "
                        "to start the tutorial or 'exit' to quit."
                    )

                else:
                    break

            # Create the tutorial project in the current working directory
            create_project("tutorial", tutorial=True)

            # Explain the tutorial project structure and how to run it
            print(
                "\nGreat! You've initialized the tutorial project.\n"
                "The project structure is as follows:\n"
                "  - ./apps/tutorial/\n"
                "    - tutorial_client.py: This is the client code that "
                "defines the behavior of the client.\n"
                "    - tutorial_server.py: This is the server code that "
                "defines the behavior of the server.\n"
                "    - config.py: This file contains the configuration for "
                "the project.\n"
                "\nTo run the tutorial server, use the following command: "
                "pyplet start\n"
                "This will start the server defined in tutorial_server.py. "
                "You can then run the client in another terminal with: python"
                " apps/tutorial/tutorial_client.py\n"
                "\nThe tutorial project will demonstrate a simple interaction"
                " between the client and the server, showcasing the core "
                "features of Pyplet. Feel free to explore the code and "
                "modify it to see how it works!"
            )

        except KeyboardInterrupt:
            print("\nTutorial stopped. Goodbye!")
            sys.exit(0)


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

    except OSError as error:
        if "[Errno 98] Address already in use" not in str(error):
            raise OSError(error)

        logger.error(
            f"The server address ({config.address}) or port ({config.port})"
            " is already binded.\n"
            "Check that no other application is using the same port "
            "or that another instance Pyplet is running."
        )
        sys.exit(3)

    except Exception as error:
        logger.error("Server error: %s", error, exc_info=True)
        sys.exit(4)

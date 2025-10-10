# Pyplet

Pyplet is an application server meant to serve interactive web applications entirely written in Python.

## Installation

To install Pyplet, clone the repository and copy the pyodide packages.

```
git clone git@git.cetic.be:seglab/pyplet.git
wget https://github.com/pyodide/pyodide/releases/download/0.28.0/pyodide-0.28.0.tar.bz2
tar -xvjf pyodide-0.28.0.tar.bz2
```

To install pyplet in your current environment, run
```
pip install -e .
```

To initialize a development environment, we propose to use `uv`, and install what is necessary to run the examples

```bash
uv venv
uv sync --group examples
```

## Running apps

You can serve the applications located in `apps/` by running the following command:

```
python -m pyplet.server
```

We advise you to take inspiration from the `apps/` folder present in this repository.

## Initialize new pyplet project
```
pyplet init <my_project_name>
```

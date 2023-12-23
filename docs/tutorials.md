

## Installing PyPSSE

Create a new python environment using the following command. Make sure you install the correct python version supported by the local PSS/e installation. Also make sure correcly choose a 32 or 64 bit python installer.

<!-- termynal -->

```
# Creating a new environment
$ conda create -n pypsse python==3.9
---> 100%
$ conda activate pypsse 

# Install the package
# For local minimal installation, use the following command
$ pip install NREL-pypsse

# For pypsse server implmentation, use
$ pip install NREL-pypsse[server]

# To use pypsse OpenMDAO interface, use
$ pip install NREL-pypsse[mdao]

# For development, in a new directory, use the following commands
$ git clone https://github.com/NREL/PyPSSE
$ conda install pygraphviz
$ pip install -e.[mdao,server,doc,dev]

```
## CLI commands

<!-- termynal -->

```
# Using the CLI
# For CLI commands, type the following command

$ pypsse --help

> Usage: pypsse [OPTIONS] COMMAND [ARGS]...
>
> PyPSSE commands
>
> Options:
>  --help  Show this message and exit.0
>
> Commands:
>  create-profiles  Creates profiles for PyPSSE project.
>  create-project   Create a new PyPSSE project.
>  run              Runs a valid PyPSSE simulation.
>  serve            Run a PyPSSE RESTful API server.
```

![type:video](https://www.youtube.com/embed/UD2oTjcpz24)

## Building a new project

<!-- termynal -->

```
# CLI project build options

$ pypsse create-project --help

> Usage: pypsse create-project [OPTIONS] PATH
>  
>   Create a new PyPSSE project.
> 
> Options:
>   -o, --overwrite                 Overwrite project is it already exists
>                                   [default: True]
>   -a, --autofill                  Attempt to auto fill settings. (Verify
>                                   manually settings file is correct)
>                                   [default: True]
>   -m, --profile-mapping TEXT      Path to a valid Profile_mapping.toml
>                                   file (used to map profile to PSSE
>                                   elements)
>   -s, --profile-store TEXT        Path to a valid Profiles.hdf5 file
>                                   (Contains profiles for time series
>                                   simulations)
>   -e, --export-settings-file TEXT
>                                   Export settings toml file path
>   -f, --simulation-file TEXT      Simulation settings toml file path
>   -F, --psse-project-folder PATH  PSS/E project folder path
>   -p, --project TEXT              project name  [required]
>   --help                          Show this message and exit.
```

### setting a new project using cli



<!-- termynal -->

```
# Building a project from scratch. Users will have to manually make all 
# required changes to the created project skeleton. 

$ pypsse create-project . -p test_project 

# Building a project from an existing PSS/e project. PyPSSE will attemp
# to autofill most settings. 

$ pypsse create-project . -p test_project -F <project path>

```

Simulation settings can be changed within the simulation_settings.toml file.

- Simution type / time / duration
- Settung upEnabling / disabling the HELICS interface
- Setting up log preferences
- Setting up simulation contingencies
- Setting up simulation storage
- Setting up simulation profiles

![type:video](https://www.youtube.com/embed/chMc9eTNO0c)

## Running a simulation 

<!-- termynal -->

```
# Project run options

$ pypsse run --help 

> Usage: pypsse run [OPTIONS] PROJECT_PATH
> 
>   Runs a valid PyPSSE simulation.

> Options:
>   -s, --simulations-file TEXT  scenario toml file to run (over rides
>                                default)  [default:
>                                simulation_settings.toml]
>   --help                       Show this message and exit.

# Running an existing PyPSSE project

$ pypsse run <project path>

```

![type:video](https://www.youtube.com/embed/oR3slhtMVX8)

## Working with a PyPSSE server

PyPSSE implments both a REST API and a Web Socket interface for the PyPSSE server. Usage of both interfaces is similar. The server can be started from the command line using the following command. 

<!-- termynal -->

```
# Starting a PyPSSE server
$ pypsse serve

> 2023-12-23 11:59:01,913 - INFO - Start PyPSSE server
> 2023-12-23 11:59:01,914 - INFO - Initializing service handler
> 2023-12-23 11:59:01,924 - INFO - Building web application
> 2023-12-23 11:59:01,932 - INFO - Building API endpoints
> INFO:     Started server process [15760]
> INFO:     Waiting for application startup.
> INFO:     Application startup complete.
> INFO:     Uvicorn running on http://127.0.0.1:9090 (Press CTRL+C to quit)

# Open the link in the browser to view API documentation (Also documented in the reference guide)
```

![type:video](https://www.youtube.com/embed/nIQapyH11KI)


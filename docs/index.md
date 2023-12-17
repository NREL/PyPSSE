
# PyPSSE

[![Build Status](https://travis-ci.org/your_username/your_package.svg?branch=master)](https://travis-ci.org/your_username/your_package)
[![PyPI version](https://badge.fury.io/py/your-package.svg)](https://badge.fury.io/py/your-package)
[![License](https://img.shields.io/badge/lincese-BSD3-blue)](https://opensource.org/licenses/BSD3)



PyPSSE is a Python wrapper around psspy—a Python application programming interface (API) for the Power System Simulator for Engineering (PSS/E)—to perform time series power flow and dynamic simulation for power systems.

The PSS/E Python API psspy follows functional programming methodology. The API exposes thousands of methods and can be difficult for new users to work with. PyPSSE wraps around hundreds of function calls in a few methods. This functionality allows users to set up cosimulations with minimal effort.

## Installation

Install using pip:

```bash
pip install pssepy
```

## Usage

Running an existing PyPSSE project from CLI

```bash
pypsse run <project path>
```

Building a new PyPSSE project from CLI

```bash
pypsse create-project <args>
```

Running a PyPSSE server

```bash
pypsse serve
```

## Features

- Supports time-series steady-state simulations, which are not inherently supported by PSS/E
- Fully supports dynamic simulations
- Built in HELICS interface (for both steady-state and dynamic simulations) enables quick cosimulation setup without a without writing a single line of code
- Command line interface allows users to create new projects, run simulations, and view reports
- Offers RESTful API interface
- Profile and result management modules allow users to interface with external profiles and mange results
- Results manger can be configured to work with PSS/E channels and psspy API calls

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## Support

If you have questions or need help, please contact [aadil.latif@nrel.gov].

## :blush: Welcome to the PyPSSE Repository

> A python wrapper around psspy (python API for PSSE simulator) to perform
> time series powerflow and dynamic simulation for power system fault

### :email: Contact Information
* :snowman: [Aadil Latif](mailto:aadil.latif@nrel.gov)
* :snowman: [Kapil Duwadi](mailto:kapil.duwadi@nrel.gov)

### :computer: Setup 

1. Clone this repository
2. Open up a Anaconda command prompt and execute command `set CONDA_FORCE_32BIT=1`.
3. Create a virtual environment by executing `conda create -n <name> python=3.7` in anaconda prompt
4. Activate environmnet by executing `conda activate <name>`
5. From the cloned PyPSSE directory execute command `python install -e.` to install PyPSSE in the same environment

### :syringe: Testing repository
1. Activate the environment
2. Execute command `pytest` from the cloned repository

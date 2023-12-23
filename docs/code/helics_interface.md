# Reference manual

PyPSSE enables out of the box integration for co-simulation and co-optimization / co-design frameworks.

## The HELICS co-simulation framework

HELICS is a scalable open-source co-simulation framework is designed to integrate simulators designed for separate TDC domains to simulate regional and interconnection-scale power system behaviors at unprecedented levels of detail and speed. 

## Setting up the HELICS co-simulation interface

To enabled the HELICS interface, set `cosimulation_mode = true` in the ``simulation_settings.toml` file.

The helics interface requires an existing HELCIS broker running either locally or remotely that the federate can connect to. Broker settings ca also be defined in the same file.

Valid HELICS interface settings are:

<img src="../models/HelicsSettings.svg" /> 

## Setting up subscriptions

Federate subscriptions can be set up by creating a `Subscription.csv`. The table below presents an example implementation.  

{{ read_csv('docs/code/subscriptions.csv') }}

## Setting up publications

Valid publiations can be defined in PyPSSE in two ways.

### Pulishing results from the result container

PyPSSE allows publication of results stored in the simulation store. Publications are set up directly in  `simulation_settings.toml` file in the PyPSSE project structure.

``` toml
[[helics.publications]]
bus_subsystems = [ 0,]
asset_type = "Buses"
asset_properties = [ "FREQ", "PU",]
```

All fields are validated against availble datasets in the simulation store. Valid model types and properties are documented [here](#models.md)

<img src="../models/PublicationDefination.svg" />

### Publishing results collected from channels

Results from channels in PSSE can also be published via the HELICS (dynamic simulation only). The setup mechanism is different.

Channels can be set up in the `export_settings.toml` file in a PyPSSE project structure.

The following data models can be refered to ensure valid implementation. Results from all channels are published to the simulation store and the HLEICS interface. 

<img src="../models/BusChannel.svg" /> 
<img src="../models/LoadChannel.svg" /> 
<img src="../models/MachineChannel.svg" /> 

Both interfaces can be used simultaneously as well

## Running the provided HELICS example 

![type:video](https://www.youtube.com/embed/gMTbxpJai7Y)
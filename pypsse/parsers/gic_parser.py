import os

import networkx as nx
import pandas as pd
from loguru import logger

from pypsse.models import SimulationSettings


class GICParser:
    """parser for the psse GIC file"""

    valid_verions = ["3"]

    def __init__(self, settings: SimulationSettings):
        """create GIC parser object

        Args:
            settings (SimulationSettings): simulation settings
        """
        logger.debug("Starting RAW parser")

        self.settings = settings
        self.filepath = str(settings.simulation.gic_file)

        self.filehandle = open(self.filepath)
        verion = self.filehandle.readline()
        if "GICFILEVRSN=" in verion:
            verion = verion.replace("GICFILEVRSN=", "").replace("\r", "").replace("\n", "")
            if verion in self.valid_verions:
                logger.debug(f"Reading GIC file verion {verion}")
            else:
                vers = ",".join(self.valid_verions)
                logger.debug(f"Version {verion} is not supported.\nFollowing version are currently supported: {vers}")
        else:
            logger.debug("GIC file structue does not seem to be valid")

        self.get_bus_coordinates()
        self.psse_graph = nx.Graph()
        self.create_graph()
        pos = {}
        for node in self.psse_graph.nodes:
            pos[node] = [
                float(self.psse_graph.nodes[node]["latitude"]),
                float(self.psse_graph.nodes[node]["longitude"]),
            ]
        export_path = os.path.join(
            self.settings["Simulation"]["Project Path"],
            "Exports",
            self.settings["Export_settings"]["NetworkX graph file"],
        )
        nx.write_gpickle(self.psse_graph, export_path)
        # nx.draw(self.psse_graph ,pos)
        # plt.show()

    def create_graph(self):
        """creates graph representation"""

        self.parse_substation_data()
        self.parse_transformer_data()
        self.parse_branch_data()
        nx.set_node_attributes(self.psse_graph, self.bus_data)

    def parse_substation_data(self):
        """parses substation data"""

        logger.debug("Parsing substation data...")
        linedata = ""
        while True:
            linedata = self.filehandle.readline()
            if "End of Bus Substation Data" in linedata:
                break
            if self.settings["GIC_export_settings"]["include substation connections"]:
                buses = linedata.replace("\r", "").replace("\n", "")
                buses = buses.split(" ")
                if buses[0] in self.bus_data and buses[1] in self.bus_data:
                    self.psse_graph.add_edge(buses[0], buses[1])
                else:
                    logger.debug(
                        f"Error parsing substation data egde: {buses}.\nOne of the bus id does not exist in bus data"
                    )

    def parse_transformer_data(self):
        """parses transformer data"""

        logger.debug("Parsing transformer data...")
        linedata = ""
        while True:
            linedata = self.filehandle.readline()
            if "End of Transformer Data" in linedata:
                break

            if self.settings["GIC_export_settings"]["include transfomer connections"]:
                buses = linedata.replace("\r", "").replace("\n", "")
                buses = buses.split(" ")[:3]
                if buses[2] == "":
                    if buses[0] in self.bus_data and buses[1] in self.bus_data:
                        self.psse_graph.add_edge(buses[0], buses[1])
                    else:
                        logger.debug(
                            f"Error parsing transformer data egde: {buses}."
                            f"\nOne of the bus id does not exist in bus data"
                        )
                else:
                    if buses[0] in self.bus_data and buses[1] in self.bus_data:
                        self.psse_graph.add_edge(buses[0], buses[1])
                    if buses[2] in self.bus_data and buses[1] in self.bus_data:
                        self.psse_graph.add_edge(buses[1], buses[2])
                    if buses[2] in self.bus_data and buses[0] in self.bus_data:
                        self.psse_graph.add_edge(buses[2], buses[0])
                    pass

    def parse_branch_data(self):
        """parses branch data"""

        logger.debug("Parsing branch data...")
        linedata = ""
        while True:
            linedata = self.filehandle.readline()
            if "End of Branch Data" in linedata:
                break
            if self.settings["GIC_export_settings"]["include branch connections"]:
                buses = linedata.replace("\r", "").replace("\n", "")
                buses = buses.split(" ")[:2]
                if buses[0] in self.bus_data and buses[1] in self.bus_data:
                    self.psse_graph.add_edge(buses[0], buses[1])
                else:
                    logger.debug(
                        f"Error parsing branch data egde: {buses}.\nOne of the bus id does not exist in bus data"
                    )

    def get_bus_coordinates(self):
        """parses bus coordinates"""

        logger.debug("Parsing bus coordinates...")
        bus_data_headers = ["subsystem/bustype?", "latitude", "longitude", "angle?"]
        self.bus_data = {}
        linedata = ""
        start = "'"
        end = "'"
        while True:
            linedata = self.filehandle.readline()
            if "End of Substation data" in linedata:
                break

            bus_name = linedata[linedata.find(start) + len(start) : linedata.rfind(end)]
            data = linedata.replace(f" {start}{bus_name}{end}", "")
            data = data.replace("  ", " ")
            data = data.replace("  ", " ")
            data = data.split(" ")
            bus_id = data[0]

            if bus_id not in self.bus_data:
                self.bus_data[bus_id] = {}

            self.bus_data[bus_id]["bus_name"] = bus_name
            for val, label in zip(data[1:], bus_data_headers):
                self.bus_data[bus_id][label] = val

        bus_data = pd.DataFrame(self.bus_data).T
        export_path = os.path.join(
            self.settings["Simulation"]["Project Path"], "Exports", self.settings["Export_settings"]["Coordinate file"]
        )
        bus_data.to_csv(export_path)
        logger.debug(f"Bus coordinate file exported to: {export_path}")

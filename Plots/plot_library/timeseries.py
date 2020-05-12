from bokeh.models import ColumnDataSource
from pyPSSE.Plots.abs_plot import abs_Plots
from bokeh.plotting import figure
from bokeh.layouts import layout
from bokeh.palettes import Plasma
from bokeh.transform import linear_cmap
import pandas as pd
import random


class timeseries(abs_Plots):
    def __init__(self, PlotProperties, Network_graph):
        super(timeseries, self).__init__(PlotProperties, Network_graph)
        self.settings = PlotProperties
        nBuses = len(self.settings["buses"])
        if nBuses > 10:
            self.settings["buses"] = self.settings["buses"][:10]
            nBuses = 10

        self.G = Network_graph
        self.pos = {
            't': [],
        }
        for b in self.settings["buses"]:
            self.pos['{}'.format(b)] = []

        self.lines_data = ColumnDataSource(self.pos)
        self.fig = figure(title='{} plot'.format(self.settings["plot_variable"]), height=self.settings['height'],
                     width=self.settings['width'], align='center',)

        self.fig.outline_line_color = None
        self.fig.toolbar.logo = None

        for i, b in enumerate(self.settings["buses"]):
            self.fig.line(x="t", y='{}'.format(b), source=self.lines_data, legend_label='bus-{}'.format(b),
                          color=Plasma[nBuses][i])

        self.fig.legend.location = "top_left"
        self.fig.legend.click_policy = "hide"

        self.layout = layout(self.fig)
        return

    def GetLayout(self):
        return self.layout

    def GetSessionID(self):
        return 0

    def Update(self, data, t):
        key = 'Buses_{}'.format(self.settings["plot_variable"])
        if key in data:
            bus_data = data[key]
            for k in self.pos:
                if k == 't':
                    self.pos[k].append(t)
                else:
                    if k in bus_data:
                        self.pos[k].append(bus_data[k])
                    else:
                        print('Data not available')
            self.lines_data.data = self.pos
        return


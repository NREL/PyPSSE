from bokeh.models import ColumnDataSource, ColorBar, FixedTicker, FuncTickFormatter, BasicTicker
from bokeh.transform import LinearColorMapper
from pyPSSE.Plots.abs_plot import abs_Plots
from bokeh.models import Range1d, HoverTool
from bokeh.models import GeoJSONDataSource
from bokeh.plotting import figure, curdoc
from bokeh.client import push_session
from bokeh.layouts import layout
import geopandas as gp
import pandas as pd
import random
import os


class heatmap(abs_Plots):
    def __init__(self, PlotProperties, Network_graph):
        super(heatmap, self).__init__(PlotProperties, Network_graph)
        self.pos = {
            'i': [],
            'x': [],
            'y': [],
            'c': [],
            'b': [],
        }

        lines = {
            'xs': [],
            'ys': [],
            'c': [],
        }

        map_pallete_index = PlotProperties['map_pallete_index']
        node_pallete_index = PlotProperties['node_pallete_index']
        line_pallete_index = PlotProperties['line_pallete_index']
        self.settings = PlotProperties

        if Network_graph:
            self.G = Network_graph
            for n in self.G.nodes:
                self.pos['i'].append(n)
                self.pos['y'].append(float(self.G.nodes[n]['latitude']))
                self.pos['x'].append(float(self.G.nodes[n]['longitude']))
                self.pos['c'].append(2)
                self.pos['b'].append(float(2.0))
            for edge in self.G.edges:
                n1, n2 = edge
                lines['ys'].append([float(self.G.nodes[n1]['latitude']), float(self.G.nodes[n2]['latitude'])])
                lines['xs'].append([float(self.G.nodes[n1]['longitude']), float(self.G.nodes[n2]['longitude'])])
                lines['c'].append(random.randint(0, 100))
        else:
            self.G = None
            coordinates = pd.read_csv(self.settings['Coordinate_file'], header=0, index_col=None).values
            r, c = coordinates.shape
            for i in range(r):
                data = coordinates[i, :]
                self.pos['i'].append(str(int(data[0])))
                self.pos['y'].append(data[1])
                self.pos['x'].append(data[2])
                self.pos['c'].append(float(2.0))
                self.pos['b'].append(data[0])



        self.scatter_data = ColumnDataSource(self.pos)

        self.TOOLTIPS = [
            ("Voltage [p.u]", "@c"),
            ("(x,y)", "(@x, @y)"),
            ("Bus id", "@i"),
        ]

        palette_scatter = self.palettes[node_pallete_index]
        self.color_mapper_scatter = LinearColorMapper(palette=palette_scatter, low=0.7, high=1.3)

        if Network_graph:
            self.lines_data = ColumnDataSource(lines)
            palette_line = self.palettes[line_pallete_index]
            self.color_mapper_lines = LinearColorMapper(palette=palette_line)

        if 'shape_file' in PlotProperties:
            shape_file = PlotProperties['shape_file']
            shp_data = gp.read_file(shape_file)

            All_states = list(shp_data['STATEFP'].values)
            WECC_states = [str(st).zfill(2) for st in [53, 41, 6, 4, 35, 8, 56, 30, 16, 49, 32]]
            Rest_states = list(set(All_states) - set(WECC_states))

            data = shp_data[shp_data["STATEFP"].isin(WECC_states)]
            data_len = len(data)
            palette = self.palettes[map_pallete_index]
            data['color'] = [random.random()/5+0. for i in range(data_len)]
            self.map_source = GeoJSONDataSource(geojson=data.to_json())
            self.color_mapper = LinearColorMapper(palette=palette)

            data_rest = shp_data[shp_data["STATEFP"].isin(Rest_states)]
            data_rest_len = len(data_rest)
            data_rest['color'] = [random.randint(0, len(palette) - 1) for i in range(data_rest_len)]
            self.map_source_rest = GeoJSONDataSource(geojson=data_rest.to_json())

        isShapefile = 'shape_file' in PlotProperties
        self.comp_map = self.create_map(isShapefile, Network_graph)
        self.layout = layout(self.comp_map)
        # self.doc = curdoc()
        # self.doc.add_root(self.layout)
        # self.doc.title = "pyPSSE"
        # self.session = push_session(self.doc)
        return

    def GetLayout(self):
        return self.layout

    def GetSessionID(self):
        return 0

    def Update(self, data, t):
        key = 'Buses_{}'.format(self.settings["plot_variable"])
        ov_id = []
        if key in data:
            bus_data = data[key]
            self.pos['c'] = [bus_data[ix] if ix in bus_data else self.pos['c'][i] for i, ix in enumerate(self.pos['i'])]
            if self.G:
                self.pos['c'] = [bus_data[ix] if ix in bus_data else self.pos['c'][i] for i, ix in enumerate(self.pos['i'])]
            else:
                update_keys = bus_data.keys()
                mod_keys = [x.replace(' ', '') for x in update_keys]
                for i, ix in enumerate(self.pos['i']):
                    if ix in mod_keys:
                        I = mod_keys.index(ix)
                        self.pos['c'][i] = bus_data[update_keys[I]]

            # for i, Vpu in enumerate(self.pos['c']):
            #     bus_id = self.pos['i'][i]
            #     if Vpu > 1.5:
            #         ov_id.append(bus_id)
            #
            # a = pd.DataFrame([ov_id])
            # a.to_csv(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model_test\Case_study\ov_buses.csv')

            self.scatter_data.data = self.pos
        else:
            print('Data not available')
        return

    def create_map(self, isShapefile, Network_graph):
        fig = figure(title='Bus {}'.format(self.settings["plot_variable"]), height=self.settings['height'],
                     width=self.settings['width'],  tools='tap,box_zoom,reset,hover', align='center',
                     tooltips=self.TOOLTIPS)
        # Add the lines to the map from our GeoJSONDataSource -object (it is important to specify the columns as 'xs' and 'ys')
        # if hide_toolbar:
        #fig.toolbar_location = None
        fig.toolbar.logo = None
        fig.xgrid.grid_line_color = None
        fig.ygrid.grid_line_color = None
        fig.xaxis.visible = False
        fig.yaxis.visible = False
        fig.outline_line_color = None

        if isShapefile:
            map = fig.patches('xs', 'ys', source=self.map_source,
                      fill_color={'field': 'color', 'transform': self.color_mapper},
                      fill_alpha=self.settings['map_alpha'], line_color="white", line_width=0.5)

            map = fig.patches('xs', 'ys', source=self.map_source_rest,
                              fill_color={'field': 'color', 'transform': self.color_mapper},
                              fill_alpha=0.2, line_color="white", line_width=0.5)

        if Network_graph:
            fig.multi_line(xs="xs", ys="ys", source=self.lines_data, line_width=0.5,
                           line_color={'field': 'c', 'transform': self.color_mapper_lines},
                           line_alpha=self.settings['line_alpha'])

        fig.circle(x='x', y='y', source=self.scatter_data, #radius=self.settings['node_size'],
                   fill_color={'field': 'c', 'transform': self.color_mapper_scatter},
                   fill_alpha=self.settings['node_alpha'], line_color="white", line_width=0.5)

        color_bar = ColorBar(color_mapper=self.color_mapper_scatter,
                             location=(0, 0),
                             orientation='horizontal',
                             padding=0,
                             # ticker=BasicTicker(desired_num_ticks=list[np.arange(0, 1.2, 0.2)]),
                             label_standoff=5,
                             )

        fig.add_layout(color_bar, 'below')

        fig.title.align = "center"
        fig.title_location = 'below'
        fig.title.text_font_size = '12pt'
        #left, right, bottom, top = -127, -66, 24, 50
        fig.x_range = Range1d(self.settings['left'], self.settings['right'])
        fig.y_range = Range1d(self.settings['bottom'], self.settings['top'])
        return fig



# dash = heatmap(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\Exports\ACTIVSg10k_graph.gpickle',
#                r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\GIS_data\tl_2017_us_state.shp',
#                0,
#                True)

from pyPSSE.Plots import plot_library
import importlib

from os.path import basename, isfile
import glob

modules = glob.glob(plot_library.__path__[0]+"/*.py")
plot_types = [ basename(f)[:-3] for f in modules if isfile(f) and
                not f.endswith('__init__.py') and
                not f.endswith('pyPlots.py')]
m ={}
for p in plot_types:
    mod = importlib.import_module(plot_library.__name__ + '.{}'.format(p))
    m[p] = mod

def create_plot(plot_type, plot_dict, network_graph):
    assert (plot_type in plot_types), "Defination for '{}' plot not found. \n " \
                                                "Please define the controller in ~pypsse\plots\Pplot_library".format(
        plot_type
    )
    PlotObject = getattr(m[plot_type], plot_type)(plot_dict, network_graph)
    return PlotObject

if __name__ == '__main__':
    import networkx as nx
    graph = nx.read_gpickle(r'C:\Users\alatif\Desktop\NEARM_sim\PSSE_studycase\PSSE_WECC_model\Exports\ACTIVSg10k_graph.gpickle')
    settings = {
        "plot" : "PU",
        "shape_file" : "C:\\Users\\alatif\\Desktop\\NEARM_sim\\PSSE_studycase\\PSSE_WECC_model\\GIS_data\\tl_2017_us_state.shp",
        "map_pallete_index" : 0,
        "node_pallete_index" : 3,
        "line_pallete_index" : 8,
        "title" : "Dynamic heatmap",
        "width" : 800,
        "height" : 600,
        "map_alpha" : 0.6,
        "line_alpha" : 0.3,
        "node_alpha" : 0.7,
        "node_size" : 0.2,
        "left" : -127,
        "right" : -66,
        "bottom" : 24,
        "top" : 50,
    }
    plots = create_plot('heatmap', settings, graph)
    from bokeh.plotting import show
    show(plots.GetLayout())

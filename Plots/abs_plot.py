from bokeh.palettes import Inferno256 , Cividis256, Plasma256, Magma256, YlGnBu9
from bokeh.palettes import Blues9, YlGnBu9, Purples9, GnBu9, BrBG11, Blues9
from abc import ABCMeta, abstractmethod

class abs_Plots:
    __metaclass__ = ABCMeta
    """An abstract class that serves as template for all pyPlot classes in :mod:`PyDSS.pyPlots.Plots` module.

    :param PlotProperties: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type PlotProperties: dict
    :param dssBuses: Dictionary of all :class:`PyDSS.dssBus.dssBus` objects in PyDSS
    :type dssBuses: dict of :class:`PyDSS.dssBus.dssBus` objects
    :param dssObjects: Dictionary of all :class:`PyDSS.dssElement.dssElement` objects in PyDSS
    :type dssObjects: dict of :class:`PyDSS.dssElement.dssElement` objects
    :param dssCircuit:  Dictionary of all :class:`PyDSS.dssCircuit.dssCircuit` objects in PyDSS
    :type dssCircuit: dict of :class:`PyDSS.dssCircuit.dssCircuit` objects
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`

    """
    palettes = {
        0: Blues9[:-3],
        1: Inferno256,
        2: Cividis256,
        3: Plasma256,
        4: Magma256,
        5: BrBG11,
        6: YlGnBu9,
        8: Purples9,
        9: GnBu9
    }

    def __init__(self, PlotProperties, Network_graph):
        """This is the constructor class.
        """
        return

    @abstractmethod
    def GetSessionID(self):
        return


    @abstractmethod
    def Update(self, data, t):
        """Method used to update the dynamic plots.
        """
        return

    @abstractmethod
    def GetLayout(self):
        return
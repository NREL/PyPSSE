from enum import IntEnum

PROFILE_VALIDATION = {
    "Load": ['PL', 'QL', 'IP', 'IQ', 'YP', 'YQ', 'PG', 'QG'],
    "Induction_machine": ['MBASE', 'RATEKV' 'PSET', 'H', 'A', 'B', 'D', 'E', 'RA', 'XA', 'XM', 'R1', 'X1', 'R2', 'X2',
                          'X3', 'E1', 'SE1', 'E2', 'SE2', 'IA1', 'IA2', 'XAMULT'],
    "Machine": ['PG', 'QG', 'QT', 'QB', 'PT', 'PB', 'MBASE', 'ZR', 'ZX', 'RT', 'XT', 'GTAP', 'F1', 'F2', 'F3', 'F4', 'WPF'],
    "Plant" : ['VS', 'RMPCT']
}

class PROFILE_TYPES(IntEnum):
    Load = 0
    Induction_machine = 1
    Machine = 2
    Plant = 3

    @staticmethod
    def names():
        return list(map(lambda c: c.name, PROFILE_TYPES))

    @staticmethod
    def values():
        return list(map(lambda c: c.value, PROFILE_TYPES))

from enum import IntEnum

class PROFILE_TYPES(IntEnum):
    Load = 0
    Generation = 1
    Irradiance = 2
    Temperature = 3
    Voltage = 4
    Current = 5
    EM_Price = 6
    AS_Price = 7
    WindProfile = 8

    @staticmethod
    def names():
        return list(map(lambda c: c.name, PROFILE_TYPES))

    @staticmethod
    def values():
        return list(map(lambda c: c.value, PROFILE_TYPES))

print(PROFILE_TYPES.values())
# Handle complex and nominal this way

NAERM_TO_PYPSSE  ={
    'Buses' : {
            'Number' : ['NUMBER'],
            'NomkV' : ['BASE'],
            'kV' : ['KV'],
            'Vpu' : ['PU'],
            'Vangle' : ['ANGLE'], # not sure whether degree or radian is expected in NAERM
            'AreaNumber' : ['AREA'],
            'ZoneNumber' : ['ZONE'],
            'AreaName' : ['AREANAME'],
            'SubLongitude' : ['LONG'], 
            'SubLatitude': ['LATI'],
            'LoadMW' : ['TOTAL', 'REAL'],
            'LoadMvar' : ['TOTAL', 'IMAG'],
            'NomB' : ['YS', 'IMAG', 'NOM'],
            'NomG' : ['YS', 'REAL', 'NOM'],
            'GenMW' : ['GENPOWER', 'REAL'],
            'GenMvar': ['GENPOWER', 'IMAG'],
            'Name' : ['NAME'],
            'Status' : ['STATUS']
    },
    'Branches' : {
        'LimitMVAA' : ['RATEA'],
        'LimitMVAB' : ['RATEB'],
        'LimitMVAC' : ['RATEC'],
        'Status' : ['STATUS'],
        'B' : ['RX', 'IMAG'],
        'BusNameFrom' : ['FROMBUSNAME'],
        'BusNumFrom' : ['FROMBUSNUM'],
        'BusNameTo' : ['TOBUSNAME'],
        'BusNumTo' : ['TOBUSNUM'],
        'Circuit' : ['CIRCUIT']
    },

    'Machines' : {
        'BusName' : ['BUSNAME'],
        'BusNum' : ['BUSNUM'],
        'ID' : ['MACID'],
        'MWMin' : ["PMIN"],
        'MWMax' : ["PMAX"],
        'MvarMin' : ["QMIN"],
        'MvarMax' : ["QMAX"],
        'MW' : ["P"],
        'Mvar' : ["Q"],
        'Status' : ["STATUS"]
    },
    "Areas" : {
        "TotalGenMW" : ["GEN", "REAL"],
        "TotalGenMvar" : ["GEN", "IMAG"]
    },
    "Zones" : {
        "TotalGenMW" : ["GEN", "REAL"],
        "TotalGenMvar" : ["GEN", "IMAG"]
    },
    "Fixed_shunts" : {
        "ShuntMW" : ["ACT", "REAL"],
        "ShuntMvar" : ["ACT", "IMAG"]
    },
    "Loads" : {
        "LoadMW" : ["MVA", "REAL"]
    }
}

import copy

def naerm_decorator(func):
    def wrapper(*args, **kwargs):

        new_args = [ag for ag in args]
        quantities = new_args[1]
        
        """ Map NAERM keys to PyPSSE keys """
        ext_string2_info = {}
        complex_conversion_dict = {}
        mapping_dict = copy.deepcopy(quantities)
        for class_name, vars in quantities.items():
            
            if class_name in NAERM_TO_PYPSSE:
                new_vars = copy.deepcopy(vars)
                for v in vars:
                    if v in NAERM_TO_PYPSSE[class_name]:
                        naerm_element_array = NAERM_TO_PYPSSE[class_name][v]
                        new_vars = [naerm_element_array[0] if el == v else el for el in new_vars]
                        
                        if len(naerm_element_array) == 3:
                            ext_string2_info[naerm_element_array[0]] = naerm_element_array[2]
                        if len(naerm_element_array)>1:
                            if class_name not in complex_conversion_dict:
                                complex_conversion_dict[class_name] = {}
                            complex_conversion_dict[class_name][v] = naerm_element_array[1]
                quantities[class_name] = new_vars
                
        """ Pass extra string info if a variable requires it """
        
        if 'ext_string2_info' not in kwargs:
            kwargs['ext_string2_info'] = {}
        elif kwargs['ext_string2_info'] is None:
            kwargs['ext_string2_info'] = {}

        kwargs['ext_string2_info'].update(ext_string2_info)
        kwargs['mapping_dict'] = mapping_dict
        new_args[1] = quantities
        new_args = tuple(new_args)
        
        """ call the core function """
        result_dict = func(*new_args, **kwargs)

        """ Convert complex values """

        for class_name_, sub_dict in result_dict.items():
            class_name, param = class_name_.split('_')[0], class_name_.split('_')[1]
            class_name_with_ = [keys for keys in NAERM_TO_PYPSSE.keys() if '_' in keys and keys in class_name_]
            if len(class_name_with_)!=0:
                class_name = class_name_with_[0]
                param = class_name_.split('_')[-1]
             
            if class_name in complex_conversion_dict:
                conv_dict = complex_conversion_dict[class_name]
                if param in conv_dict:
                    for key, value in sub_dict.items():
                        if isinstance(value, complex):
                            if conv_dict[param] == 'REAL':
                                sub_dict[key] = value.real
                            elif conv_dict[param] == 'IMAG':
                                sub_dict[key] = value.imag

        return result_dict

    return wrapper
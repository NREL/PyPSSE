from typing import List

from loguru import logger

from pypsse.common import MAPPED_CLASS_NAMES


class Reader:
    "Parser for indexing all PSSE model assets"

    def __init__(self, psse_instance: object):
        """creates pypsse model reader

        Args:
            psse_instance (object): simulator instance
        """
        self.psse = psse_instance
        self.buses = self.get_data("abus", tails=["int"], strings=["NUMBER"], flags=[2])
        self.loads = self.get_data("aload", tails=["int", "char"], strings=["NUMBER", "ID"], flags=[4, 4])
        self.loads = self.get_data("aload", tails=["int", "char"], strings=["NUMBER", "ID"], flags=[4, 4])
        self.fixed_stunts = self.get_data("afxshunt", tails=["int", "char"], strings=["NUMBER", "ID"], flags=[4, 4])
        self.generators = self.get_data("amach", tails=["int", "char"], strings=["NUMBER", "ID"], flags=[4, 4])
        self.branches = self.get_data(
            "abrn", tails=["int", "int", "char"], strings=["FROMNUMBER", "TONUMBER", "ID"], flags=[2, 2, 2]
        )
        self.transformers = self.get_data(
            "atr3", tails=["int", "int", "int"], strings=["WIND1NUMBER", "WIND2NUMBER", "WIND3NUMBER"], flags=[2, 2, 2]
        )
        self.area = self.get_data(
            "aarea", tails=["int", "char"], strings=["NUMBER", "AREANAME"], flags=[2, 2]
        )  # Talk to Aadil
        self.dc_branch = self.get_data(
            "a2trmdc", tails=["int", "int"], strings=["FROMNUMBER", "TONUMBER"], flags=[2, 2]
        )  # three terminal dc lines not implemented
        self.multi_term_dc = self.get_data(
            "amultitrmdc", tails=["int", "int"], strings=["VCNPOSNUMBER", "VCNNEGNUMBER"], flags=[2, 2]
        )
        self.switched_shunt = self.get_data(
            "aswsh", tails=["int", "char"], strings=["NUMBER", "DEVICENAME"], flags=[4, 4]
        )
        self.zones = self.get_data("azone", tails=["int", "char"], strings=["NUMBER", "ZONENAME"], flags=[2, 2])
        self.owners = self.get_data("aowner", tails=["int", "char"], strings=["NUMBER", "OWNERNAME"], flags=[2, 2])

    def get_data(self, func_name: str, tails: list = [], strings: list = [], flags: List[int] = []) -> list:
        """returns list of assets matching signature

        Args:
            func_name (str): _description_
            tails (list, optional): method tail. Defaults to [].
            strings (list, optional): data types. Defaults to [].
            flags (List[int], optional): list of flags for filtering. Defaults to [].

        Returns:
            list: list of asset names
        """

        array_list = []
        for tail, string, flag in zip(tails, strings, flags):
            func = getattr(self.psse, func_name.lower() + tail)
            ierr, array_1 = func(sid=-1, flag=flag, string=string)
            assert ierr == 0, f"Error code {ierr}, while running function '{func_name.lower() + tail}'"
            array_list.append([x for array in array_1 for x in array])

        logger.info(f"{func_name} count - {len(array_1)}")
        if len(array_list) == 1:
            return array_list[0]

        return list(zip(*array_list))

    def __str__(self) -> str:
        """overrides default 'print' behavior

        Returns:
            str: summary of model assets
        """
        str_name = "Model asset summary:\n"
        for model in MAPPED_CLASS_NAMES:
            str_name += f"   {model}-{len(getattr(self, model))}"
        return str_name

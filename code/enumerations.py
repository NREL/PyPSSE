""" This module contains class for auto documenting pydantic classes."""

# standard imports
import enum
import logging
from pathlib import Path

# third-party imports
from mdutils.mdutils import MdUtils

# internal imports
from pypsse import enumerations

folder_path = Path(__file__).parent


class PydanticDocBuilder:
    """Builder class for automatically documenting pydantic classes."""

    def __init__(self, md_filename="enumerations"):
        asset_list = self.create_schema_diagrams(md_filename)
        self.create_markdown_file(md_filename, asset_list)

    def create_schema_diagrams(self, md_filename):
        """Method to create schema diagrams."""
        asset_list = {}
        for asset in dir(enumerations):
            if not asset.startswith("_") and asset != "BaseModel":
                model = getattr(enumerations, asset)
                if isinstance(model, type):
                    if issubclass(model, enum.Enum or enum.IntEnum):
                        print(model.__name__, True)
                        if model.__name__ not in asset_list:
                            asset_list[model.__name__] = {}
                        for m in model:
                            asset_list[model.__name__][m.name] = m.value
                    else:
                        print(model.__name__, False)
        return asset_list

    def create_markdown_file(self, md_filename, asset_list):
        """Method to create markdown file."""
        md_file_path = folder_path / md_filename
        md_file = MdUtils(file_name=str(md_file_path))
        md_file.new_header(level=1, title="Libray Enumerations")
        md_file.new_paragraph(
            "This page provides details on the enumerated classes part of the PyPSSE library."
            "Enumerations map directly to ."
            )

        md_file.new_paragraph()
        for asset_name, table_data in asset_list.items():
            md_file.write(f"## {asset_name}\n")
            md_file.write(" \n")
            list_of_strings = ["Key", "Value"]
            for k, v in table_data.items():
                list_of_strings.extend([f"pypsse.enumerations.{asset_name}.{k}", str(v)])
            md_file.new_line()
            n_rows = int(len(list_of_strings) / 2)
            md_file.new_table(columns=2, rows=n_rows, text=list_of_strings, text_align='left')
            md_file.write(" \n")

        md_file.write(" \n")
        md_file.create_md_file()


PydanticDocBuilder()

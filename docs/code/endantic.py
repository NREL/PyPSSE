# """ This module contains class for auto documenting pydantic classes."""

# # standard imports
# from pathlib import Path

# # third-party imports
# import erdantic as erd
# from mdutils import Html
# from mdutils.mdutils import MdUtils
# from pydantic import BaseModel

# # internal imports
# import cadet_opt.interface.dist_assets as assets

# folder_path = Path(__file__).parent


# class PydanticDocBuilder:
#     """Builder class for automatically documenting pydantic classes."""

#     def __init__(self, md_filename="models"):
#         asset_list = self.create_schema_diagrams(md_filename)
#         self.create_markdown_file(md_filename, asset_list)

#     def create_schema_diagrams(self, md_filename):
#         """Method to create schema diagrams."""
#         asset_list = {}
#         for asset in dir(assets):
#             if not asset.startswith("_") and asset != "BaseModel":
#                 model = getattr(assets, asset)
#                 if isinstance(model, type):
#                     if issubclass(model, BaseModel):
#                         file_fath = folder_path / md_filename / f"{asset}.svg"
#                         diagram = erd.create(model)
#                         diagram.draw(file_fath)
#                         asset_list[asset] = f"{asset}.svg"
#         return asset_list

#     def create_markdown_file(self, md_filename, asset_list):
#         """Method to create markdown file."""
#         md_file_path = folder_path / md_filename
#         md_file = MdUtils(file_name=str(md_file_path))
#         md_file.new_header(level=1, title="Reference manual")
#         md_file.new_paragraph(
#             "This page provides details on"
#             "the data models part of the Cadet-OPT library."
#         )
#         md_file.new_paragraph()
#         for asset_name, asset_schema_path in asset_list.items():
#             md_file.new_paragraph(Html.image(path=asset_schema_path))
#             md_file.write(" \n")
#             md_file.write(f"::: cadet_opt.interface.dist_assets.{asset_name}\n")
#             md_file.write(" \n")

#         md_file.write(" \n")
#         md_file.create_md_file()


# PydanticDocBuilder()

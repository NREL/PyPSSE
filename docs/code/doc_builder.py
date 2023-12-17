# from pathlib import Path
# import mkdocs_gen_files

# src_root = Path("pypsse")
# print(src_root.absolute())
# for path in src_root.glob("**/*.py"):
#     doc_path = Path("docs/reference", path.relative_to(src_root)).with_suffix(".md")

#     if "__init__" not in str(doc_path):
#         if doc_path.is_dir():
#             doc_path.parent.mkdir(parents=True, exist_ok=True)
#         else:


#         with mkdocs_gen_files.open(doc_path, "w") as f:
#             ident = ".".join(path.with_suffix("").parts)
#             print("::: " + ident, file=f)

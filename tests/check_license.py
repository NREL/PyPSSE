import os
import shutil
import sys

from pypsse.Simulator import Simulator


def empty_folder(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        example_path = sys.argv[1]
    else:
        example_path = "./examples/static_example"
    toml_path = os.path.join(example_path, "Settings", "simulation_settings.toml")
    export_path = os.path.join(example_path, "Exports")
    empty_folder(export_path)
    x = Simulator(toml_path)
    x.init()
    x.run()

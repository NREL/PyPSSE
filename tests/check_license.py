from pypsse.pyPSSE_instance import pyPSSE_instance
import os


print(os.getcwd())
x = pyPSSE_instance("./examples/static_example")
x.init()
x.run()

from setuptools import setup
import platform

PACKAGEDATA={
    "name":  "pych341",
    "version":  "0.1",
    "keywords":  ["pych341",],
    "description":  "python bindings of ch341",
    "long_description":  "python bindings of ch341",
    "license":  "MIT Licence",

    "author":"云line",

    "include_package_data":  True,
    "platforms":  ["windows"],
    "install_requires":  [],
}

data_aa64={   
    "packages":  ['ch341','ch341.examples','ch341.lib'],
    "package_data":{'ch341.lib':['libch347.so']},
    "package_dir":{'ch341.lib':'./lib/linux/aarch64'},
}

data_win={
    "packages":  ['ch341','ch341.examples'],
}

if platform.system()=="Windows":
    PACKAGEDATA.update(data_win)
elif platform.system()=="Linux":
    PACKAGEDATA.update(data_aa64)

setup(**PACKAGEDATA)
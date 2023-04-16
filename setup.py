from setuptools import setup, find_packages

setup(
    name="pych341",
    version="0.1",
    keywords=[
        "pych341",
    ],
    description="python bindings of ch341",
    long_description="python bindings of ch341",
    license="MIT Licence",
    author="超级猫猫",
    packages=["ch341", "ch341.examples"],
    include_package_data=True,
    platforms=["windows"],
    install_requires=[],
)

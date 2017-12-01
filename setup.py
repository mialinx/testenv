#!/usr/bin/python

from setuptools import setup
setup(
    name = "testenv",
    version = "0.09",
    packages = ['testenv', 'testenv.contrib'],
    scripts = ['scripts/testenv'],
    author = "Dmitry Smal",
    author_email = "mialinx@gmail.com",
    description = "Tool to setup test environment for unit tests",
    license = "MIT",
    url = "https://github.com/mialinx/testenv",
    install_requires=[
        "PyYAML >= 3.11",
    ]
)

#!/usr/bin/env python
import os
import json
from setuptools import setup

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [ byteify(element) for element in input ]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def cleaned_path(path):
  if path.endswith("/"):
    path = path[:-1]
  if path.startswith("="):
    path = path[1:]
  realpath = os.path.realpath(path)
  return realpath

def read_json(path):
    try:
        with open(cleaned_path(path), "r") as jsonFile:
          jsondata = json.load(jsonFile)
          jsonFile.seek(0)
        return byteify(jsondata)
    except:
        print("Error! json file '{0}' does not exist!".format(cleaned_path(path)))
        return None

dashconfig = read_json(os.path.join(os.path.dirname(__file__), "config.json"))

setup(
    name=dashconfig["name"],
    version=dashconfig["version"],
    author=dashconfig["author"],
    author_email=dashconfig["author_email"],
    description=dashconfig["description"],
    classifiers=dashconfig["classifiers"],
    keywords=dashconfig["keywords"],
    packages=dashconfig["packages"],
    install_requires=dashconfig["install_requires"],
    data_files=dashconfig["data_files"],
    include_package_data=dashconfig["include_package_data"]
)

#!/bin/sh
rm -rf dist
rm -rf doc
doxygen
python3 -m pip install --upgrade build
python3 -m build
cp -rf dist/* dist.done/
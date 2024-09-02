#!/bin/bash
set -e
rm -rf dist/*.whl
rm -rf dist
pyflakes3 pbackup/*.py
doxygen
poetry -vvv build

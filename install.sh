#!/bin/sh
set -e

#Check the python files and exit on error.
python3 -m pyflakes pbackup/*.py

# Install only for current user
#python3 -m pip install .

#install for all users
sudo python3 -m pip install .


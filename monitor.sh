#!/bin/bash

set -e
cd $(dirname $0)

docker-compose -f docker-compose.yml -p carmomaq up -d
python3 monitor.py

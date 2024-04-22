#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

/dls_sw/work/odin/xspress3odin/xspress-detector/venv/bin/xspress_live_merge --sub_ports 15500,15501

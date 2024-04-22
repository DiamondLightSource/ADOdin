#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

/dls_sw/prod/tools/RHEL7-x86_64/odin-data/1.9.0+dls2/prefix/bin/frameReceiver --sharedbuf=odin_buf_1 -m 1048576000 --iothreads 1 --ctrl=tcp://0.0.0.0:10000 --ready=tcp://127.0.0.1:10001 --release=tcp://127.0.0.1:10002 --json_file=$SCRIPT_DIR/fr1.json --logconfig $SCRIPT_DIR/log4cxx.xml

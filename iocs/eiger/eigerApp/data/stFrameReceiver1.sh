#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

/dls_sw/prod/tools/RHEL7-x86_64/odin-data/1.10.1+dls1/prefix/bin/frameReceiver --io-threads 2 --ctrl=tcp://0.0.0.0:10000 --config=$SCRIPT_DIR/fr1.json --log-config $SCRIPT_DIR/log4cxx.xml

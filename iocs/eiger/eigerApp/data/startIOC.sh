#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
IOC_ROOT="$SCRIPT_DIR/../.."
IOC_NAME="$(echo $IOC_ROOT | sed 's/.*iocs\///g' | sed 's/\/.*//g')"

$IOC_ROOT/bin/linux-x86_64/st$IOC_NAME.sh 6064

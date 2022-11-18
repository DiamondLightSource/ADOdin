#!/bin/sh

if [[ "sim" == "$1" || "lab" == "$1" ]] ; then
    echo starting $1
else
    echo "Usage: $0 [sim|lab]"
    echo
    echo sim: starts the simulation detector locally
    echo lab: should be run on lab29-tristan01 and connects to the arc detector
    exit 1
fi

# a script for starting Arc FR, FP, Meta, OdinServer on a server
# (DLS servers do not have gnome terminal so startAll.sh does not work)
#
# this uses zellij which is a little easier to use than tmux

# this makes it easier to run python projects on multiple machines
# without having to release a lightweight virtual env to production
# NOTE: this environment variable must be set when the build is run too
export PIPENV_VENV_IN_PROJECT=enabled

export THIS_DIR="$(realpath $(dirname ${BASH_SOURCE[0]}))"
export SESSION="ArcOdin"

export SCRIPT_DIR=$THIS_DIR/../../iocs/arc-${1}/arc-${1}App/data
cd ${SCRIPT_DIR}

# note this section can be copied from ioc's startAll.sh ##############
export IOC_ROOT="$SCRIPT_DIR/../.."
export IOC_NAME="$(echo $IOC_ROOT | sed 's/.*iocs\///g' | sed 's/\/.*//g')"
export FR1="${SCRIPT_DIR}/stFrameReceiver1.sh"
export FP1="${SCRIPT_DIR}/stFrameProcessor1.sh"
export MetaWriter="${SCRIPT_DIR}/stMetaWriter.sh"
export OdinServer="$SCRIPT_DIR/stOdinServer.sh"
export IOC="$IOC_ROOT/bin/linux-x86_64/st$IOC_NAME.sh 6064"
# end of copy section #################################################

# this assumes arc-detector is a peer to ADODin
# TODO - make a sim launcher scirpt in arc.py
export SIM_DIR=${THIS_DIR}/../../../arc-detector/control/

export sim="${THIS_DIR}/../../../venv/bin/arc_simulator"
if [ "${1}" != "sim" ] ; then
    export sim="echo start simulator with $sim"
fi

export SHELL=bash
cd ${SCRIPT_DIR}
/dls_sw/work/wqi71457/Arc/zellij --layout ${THIS_DIR}/layout.kdl


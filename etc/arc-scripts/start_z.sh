#!/bin/sh 

# a script for starting Arc FR, FP, Meta, OdinServer on a server
# (DLS servers do not have gnome terminal so startAll.sh does not work) 
#
# this uses zellij which is a little easier to use than tmux

export THIS_DIR="$(realpath $(dirname ${BASH_SOURCE[0]}))"
export SESSION="ArcOdin"

# SCRIPT_DIR=$THIS_DIR/iocs/arc-lab/arc-labApp/data
export SCRIPT_DIR=$THIS_DIR/../../iocs/arc/arcApp/data
 
# note this section can be copied from ioc's startAll.sh ##############
export IOC_ROOT="$SCRIPT_DIR/../.."
export IOC_NAME="$(echo $IOC_ROOT | sed 's/.*iocs\///g' | sed 's/\/.*//g')"
export FR1="${SCRIPT_DIR}/stFrameReceiver1.sh"
export FP1="${SCRIPT_DIR}/stFrameProcessor1.sh"
export MetaWriter="${SCRIPT_DIR}/stMetaWriter.sh"
export OdinServer="$SCRIPT_DIR/stOdinServer.sh"
export IOC="$IOC_ROOT/bin/linux-x86_64/st$IOC_NAME.sh 6064"
# end of copy section #################################################

function launch_sim {
    cd /dls_sw/work/Arc/arc-detector/control/ 
    pipenv run arc_simulator
}

/home/hgv27681/bin/zellij --layout-path ${THIS_DIR}/layout.yml

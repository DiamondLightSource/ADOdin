#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
IOC_ROOT="$SCRIPT_DIR/../.."
IOC_NAME="$(echo $IOC_ROOT | sed 's/.*iocs\///g' | sed 's/\/.*//g')"

EigerFan="${SCRIPT_DIR}/stEigerFan.sh"
FR1="${SCRIPT_DIR}/stFrameReceiver1.sh"
FP1="${SCRIPT_DIR}/stFrameProcessor1.sh"
FR2="${SCRIPT_DIR}/stFrameReceiver2.sh"
FP2="${SCRIPT_DIR}/stFrameProcessor2.sh"
FR3="${SCRIPT_DIR}/stFrameReceiver3.sh"
FP3="${SCRIPT_DIR}/stFrameProcessor3.sh"
FR4="${SCRIPT_DIR}/stFrameReceiver4.sh"
FP4="${SCRIPT_DIR}/stFrameProcessor4.sh"
MetaWriter="${SCRIPT_DIR}/stMetaWriter.sh"
# read at end helps diagnose issues by keeping the terminal open after exit
OdinServer="$SCRIPT_DIR/stOdinServer.sh; read"
IOC="$IOC_ROOT/bin/linux-x86_64/st$IOC_NAME.sh 6064"

gnome-terminal --tab --title="EigerFan" -- bash -c "${EigerFan}"
gnome-terminal --tab --title="FR1" -- bash -c "${FR1}"
gnome-terminal --tab --title="FP1" -- bash -c "${FP1}"
gnome-terminal --tab --title="FR2" -- bash -c "${FR2}"
gnome-terminal --tab --title="FP2" -- bash -c "${FP2}"
gnome-terminal --tab --title="FR3" -- bash -c "${FR3}"
gnome-terminal --tab --title="FP3" -- bash -c "${FP3}"
gnome-terminal --tab --title="FR4" -- bash -c "${FR4}"
gnome-terminal --tab --title="FP4" -- bash -c "${FP4}"
gnome-terminal --tab --title="MetaWriter" -- bash -c "${MetaWriter}"
sleep 1
gnome-terminal --tab --title="OdinServer" -- bash -c "$OdinServer"
sleep 1
gnome-terminal --tab --title="IOC" -- bash -c "$IOC"

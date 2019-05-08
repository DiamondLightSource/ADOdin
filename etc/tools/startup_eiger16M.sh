#!/bin/bash

IOC="eiger16M"
DETECTOR="/dls_sw/prod/tools/RHEL7-x86_64/eiger-detector/1-5-0"
ODIN_DATA="/dls_sw/prod/tools/RHEL7-x86_64/odin-data/1-1-0dls3"

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
ROOT="${SCRIPT_DIR}/../.."
DATA="${ROOT}/iocs/${IOC}/${IOC}App/data"

Fan="${DATA}/stEigerFan.sh"
FR1="${DATA}/stFrameReceiver1.sh"
FR2="${DATA}/stFrameReceiver2.sh"
FR3="${DATA}/stFrameReceiver3.sh"
FR4="${DATA}/stFrameReceiver4.sh"
FP1="${DATA}/stFrameProcessor1.sh"
FP2="${DATA}/stFrameProcessor2.sh"
FP3="${DATA}/stFrameProcessor3.sh"
FP4="${DATA}/stFrameProcessor4.sh"
MetaListener="export PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages:${ODIN_DATA}/prefix/lib/python2.7/site-packages &&
              ${DATA}/stEigerMetaListener.sh"
OdinServer="export PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages:${ODIN_DATA}/prefix/lib/python2.7/site-packages &&
            ${DATA}/stOdinServer.sh"
IOC="${ROOT}/iocs/${IOC}/bin/linux-x86_64/st${IOC}.sh"

gnome-terminal --tab --title="Fan"          -- bash -c "${Fan}"
gnome-terminal --tab --title="FR1"          -- bash -c "${FR1}"
gnome-terminal --tab --title="FR2"          -- bash -c "${FR2}"
gnome-terminal --tab --title="FR3"          -- bash -c "${FR3}"
gnome-terminal --tab --title="FR4"          -- bash -c "${FR4}"
gnome-terminal --tab --title="FP1"          -- bash -c "${FP1}"
gnome-terminal --tab --title="FP2"          -- bash -c "${FP2}"
gnome-terminal --tab --title="FP3"          -- bash -c "${FP3}"
gnome-terminal --tab --title="FP4"          -- bash -c "${FP4}"
gnome-terminal --tab --title="MetaListener" -- bash -c "${MetaListener}"
gnome-terminal --tab --title="OdinServer"   -- bash -c "${OdinServer}"
sleep 5
gnome-terminal --tab --title="IOC"          -- bash -c "${IOC}"

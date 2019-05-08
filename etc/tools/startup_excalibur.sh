#!/bin/bash

IOC="excalibur"
DETECTOR="/dls_sw/prod/tools/RHEL7-x86_64/excalibur-detector/0-6-0"
ODIN_DATA="/dls_sw/prod/tools/RHEL7-x86_64/odin-data/1-1-0dls3"

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
ROOT="${SCRIPT_DIR}/../.."
APPS="${ROOT}/iocs/${IOC}/${IOC}App/data"

FR1="${APPS}/stFrameReceiver1.sh"
FR2="${APPS}/stFrameReceiver2.sh"
FP1="${APPS}/stFrameProcessor1.sh"
FP2="${APPS}/stFrameProcessor2.sh"
OdinServer="PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages:${ODIN_DATA}/prefix/lib/python2.7/site-packages ${APPS}/stOdinServer.sh"
IOC="${ROOT}/iocs/${IOC}/bin/linux-x86_64/st${IOC}.sh"

gnome-terminal --tab --title="FR1"        -- /bin/bash -c "${FR1}"
gnome-terminal --tab --title="FR2"        -- /bin/bash -c "${FR2}"
gnome-terminal --tab --title="FP1"        -- /bin/bash -c "${FP1}"
gnome-terminal --tab --title="FP2"        -- /bin/bash -c "${FP2}"
gnome-terminal --tab --title="OdinServer" -- /bin/bash -c "${OdinServer}"
sleep 5
gnome-terminal --tab --title="IOC"        -- /bin/bash -c "${IOC}"

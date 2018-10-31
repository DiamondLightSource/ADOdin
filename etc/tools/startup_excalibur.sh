#!/bin/bash

IOC="excalibur"
DETECTOR="/dls_sw/work/tools/RHEL6-x86_64/odin/excalibur-detector"
ODIN_DATA="/dls_sw/work/tools/RHEL6-x86_64/odin/mef65357/odin-data"

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
ROOT="${SCRIPT_DIR}/../.."
APPS="${ROOT}/iocs/${IOC}/${IOC}App/data"

FR1="cd ${APPS} && ./stFrameReceiver1.sh"
FR2="cd ${APPS} && ./stFrameReceiver2.sh"
FP1="cd ${APPS} && ./stFrameProcessor1.sh"
FP2="cd ${APPS} && ./stFrameProcessor2.sh"
OdinServer="export PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages:${ODIN_DATA}/prefix/lib/python2.7/site-packages &&
            cd ${APPS} && ./stOdinServer.sh"
IOC="sleep 3 && cd ${ROOT}/iocs/${IOC} && bin/linux-x86_64/st${IOC}.sh"

gnome-terminal --tab --title="FR1"          -e "bash -c '$FR1; $SHELL'" \
               --tab --title="FR2"          -e "bash -c '$FR2; $SHELL'" \
               --tab --title="FP1"          -e "bash -c '$FP1; $SHELL'" \
               --tab --title="FP2"          -e "bash -c '$FP2; $SHELL'" \
               --tab --title="OdinServer"   -e "bash -c '$OdinServer; $SHELL'" \
               --tab --title="IOC"          -e "bash -c '$IOC; $SHELL'"

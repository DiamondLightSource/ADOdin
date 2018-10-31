#!/bin/bash

IOC="eiger16M"
DETECTOR="/dls_sw/work/tools/RHEL6-x86_64/eiger-detector"
ODIN_DATA="/dls_sw/work/tools/RHEL6-x86_64/odin/mef65357/odin-data"

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
ROOT="${SCRIPT_DIR}/../.."
DATA="${ROOT}/iocs/${IOC}/${IOC}App/data"

Fan="cd ${DATA} && ./stEigerFan.sh"
FR1="cd ${DATA} && ./stFrameReceiver1.sh"
FR2="cd ${DATA} && ./stFrameReceiver2.sh"
FR3="cd ${DATA} && ./stFrameReceiver3.sh"
FR4="cd ${DATA} && ./stFrameReceiver4.sh"
FP1="cd ${DATA} && ./stFrameProcessor1.sh"
FP2="cd ${DATA} && ./stFrameProcessor2.sh"
FP3="cd ${DATA} && ./stFrameProcessor3.sh"
FP4="cd ${DATA} && ./stFrameProcessor4.sh"
MetaListener="export PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages &&
              cd ${DATA} && ./stEigerMetaListener.sh"
OdinServer="export PYTHONPATH=${DETECTOR}/prefix/lib/python2.7/site-packages:${ODIN_DATA}/prefix/lib/python2.7/site-packages &&
            cd ${DATA} && ./stOdinServer.sh"
IOC="sleep 3 && cd ${ROOT}/iocs/${IOC} && bin/linux-x86_64/st${IOC}.sh"

gnome-terminal --tab --title="Fan"          -e "bash -c '$Fan; $SHELL'" \
               --tab --title="FR1"          -e "bash -c '$FR1; $SHELL'" \
               --tab --title="FR2"          -e "bash -c '$FR2; $SHELL'" \
               --tab --title="FR3"          -e "bash -c '$FR3; $SHELL'" \
               --tab --title="FR4"          -e "bash -c '$FR4; $SHELL'" \
               --tab --title="FP1"          -e "bash -c '$FP1; $SHELL'" \
               --tab --title="FP2"          -e "bash -c '$FP2; $SHELL'" \
               --tab --title="FP3"          -e "bash -c '$FP3; $SHELL'" \
               --tab --title="FP4"          -e "bash -c '$FP4; $SHELL'" \
               --tab --title="MetaListener" -e "bash -c '$MetaListener; $SHELL'" \
               --tab --title="OdinServer"   -e "bash -c '$OdinServer; $SHELL'" \
               --tab --title="IOC"          -e "bash -c '$IOC; $SHELL'"

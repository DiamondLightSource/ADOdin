#!/bin/sh 

# a script for starting Arc FR, FP, Meta, OdinServer on a server
# (DLS servers do not have gnome terminal so startAll.sh does not work) 
#
# if you add the following to ~/.tmux.conf then you can move around
# the panes with ctrl h, ctrl j for horizontal and vertical switching
#
# bind -n C-h select-pane -L
# bind -n C-j select-pane -D
#
# also important 'ctrl-b [' switch to scroll mode (using mouse wheel)
# q or esc to return to normal mode

export WORK_DIR="$(realpath $(dirname ${BASH_SOURCE[0]}))"
export SESSION="ArcOdin"

SCRIPT_DIR=$WORK_DIR/iocs/arc-lab/arc-labApp/data

# note this section can be copied from ioc's startAll.sh ##############
IOC_ROOT="$SCRIPT_DIR/../.."
IOC_NAME="$(echo $IOC_ROOT | sed 's/.*iocs\///g' | sed 's/\/.*//g')"
FR1="${SCRIPT_DIR}/stFrameReceiver1.sh"
FP1="${SCRIPT_DIR}/stFrameProcessor1.sh"
MetaWriter="${SCRIPT_DIR}/stMetaWriter.sh"
OdinServer="$SCRIPT_DIR/stOdinServer.sh"
IOC="$IOC_ROOT/bin/linux-x86_64/st$IOC_NAME.sh 6064"
# end of copy section #################################################

tmux kill-session -t $SESSION
tmux new-session -s $SESSION -d 'bash'
tmux split-window -t$SESSION:0.0 -p 75 -v "bash -c ${FR1}"
tmux split-window -t$SESSION:0.1 -v       "bash -c ${FP1}"
tmux split-window -t$SESSION:0.1 -h       "bash -c $OdinServer"
tmux split-window -t$SESSION:0.2 -h       "bash -c ${MetaWriter}"
tmux -2 attach-session -t $SESSION -d

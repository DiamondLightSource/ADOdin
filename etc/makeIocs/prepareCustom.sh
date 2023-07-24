sed -e '2i export EPICS_CA_SERVER_PORT=6064' \
    -e '2i export EPICS_CA_REPEATER_PORT=6065' \
    -i $1/${2}App/opi/edl/st${2}-gui

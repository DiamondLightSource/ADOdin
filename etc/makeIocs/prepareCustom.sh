sed -e '7i export hostname=$(hostname -s)\' \
    -i $1/iocBoot/ioc${2}/st${2}.sh
sed -e "s/.*.db'/&, hostname=\$(hostname)/" \
    -i $1/iocBoot/ioc${2}/st${2}.src
sed -e "s/ODN.edl/-m hostname=\$(hostname -s) ODN.edl/" \
    -e '2i export EPICS_CA_SERVER_PORT=6064' \
    -e '3i export EPICS_CA_REPEATER_PORT=6065' \
    -i $1/${2}App/opi/edl/st${2}-gui

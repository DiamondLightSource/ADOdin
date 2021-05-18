sed -e '7i export hostname=$(hostname -s)\' \
    -i $1/iocBoot/ioc${2}/st${2}.sh
sed -e "s/.*.db'/&, hostname=\$(hostname)/" \
    -i $1/iocBoot/ioc${2}/st${2}.src
sed -e "s/edm \${OPTS}/edm \${OPTS} -m hostname=\$(hostname -s)/" \
    -e '2i export EPICS_CA_SERVER_PORT=6064' \
    -e '2i export EPICS_CA_REPEATER_PORT=6065' \
    -i $1/${2}App/opi/edl/st${2}-gui

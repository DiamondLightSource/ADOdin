#!/bin/bash

numactl --membind=0 --cpunodebind=0 /dls_sw/prod/python3/RHEL7-x86_64/eiger-detector/1.13.0+dls1/prefix/bin/eiger_meta_writer -w eiger_detector.EigerMetaWriter --sensor-shape 4362 4148 --data-endpoints tcp://127.0.0.1:10008,tcp://127.0.0.1:10018,tcp://127.0.0.1:10028,tcp://127.0.0.1:10038 --static-log-fields beamline=${BEAMLINE},detector="Eiger16M" --log-server "graylog-log-target.diamond.ac.uk:12210"

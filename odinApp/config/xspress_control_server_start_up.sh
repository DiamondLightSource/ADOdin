#!/bin/bash
SCRIPT_DIR="$$( cd "$$( dirname "$$0" )" && pwd )"
LD_LIBRARY_PATH=$XSPRESS_DETECTOR/control/libxspress-wrapper/support/ $XSPRESS_DETECTOR/bin/xspressControl -j $$SCRIPT_DIR/xspress.json
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
LD_LIBRARY_PATH=/dls_sw/work/odin/xspress3odin/xspress-detector/vscode_prefix/control/libxspress-wrapper/support/ /dls_sw/work/odin/xspress3odin/xspress-detector/vscode_prefix/bin/xspressControl -j $SCRIPT_DIR/xspress.json
#!/usr/bin/env bash

set -e

# Can be used like this: VLOG_ARGS=+define+USE_JTAG_DPI ./compile.sh


vsim-10.7b -c -do 'source compile.tcl; quit'

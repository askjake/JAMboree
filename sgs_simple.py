#!/usr/bin/env python3
#
# executes simple SGS command that has no parameters
#  (only 'receiver' 'cid' and 'command' fields required)
#
# Usage
#  ./sgs_simple.py [-i STB_IP] command
#
# Example
#   ./sgs_ae.py get_network_diagnosis_metrics
#   ./sgs_ae.py -i 192.168.1.24 get_network_diagnosis_metrics
#

from sgs_lib import *
import signal
import sys
import argparse

# Ctrl-C handler
def signal_handler(sig, frame):
   print('Exiting')
   sys.exit(0)

# get params
parser = sgs_arg_parse(description="execute simple SGS command (with no extra params)")
parser.add_argument("command", help="SGS command to execute")
args = parser.parse_args()

# fill in key variables
stb = STB(args)


data = stb.sgs_command({"command": args.command})
if not data:
   print ("error")
   quit()

result = data['result']
if result:
   print (json.dumps(data, indent=2, separators=("","\t")))

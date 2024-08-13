#!/usr/bin/env python3
#
# Gets STB IP mode
#
# Usage
#  ./get_mdu_mode.py [ip]
#   where 
#      - ip - is STB IP
#
# Example
#   ./get_mdu_mode.py 192.168.1.24

from sgs_lib import *
import argparse

# get params
parser = sgs_arg_parse(description="get MDU mode - sat or ip")
args = parser.parse_args()

stb = STB(args)

querry = {"command":"get_stb_settings","name":"dish_ip_mode","id":63}

data = stb.sgs_command(querry)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  quit()


info = data['data']
mode = info['enable']

if 1 == mode:
   print ("MDU mode")
else:
   print ("SAT mode")


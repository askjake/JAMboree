#!/usr/bin/env python3
#
# execute SGS command
#
# Usage
#  ./sgs.py [-i IP] query
#   where 
#      - IP - is STB IP
#      - query - actually SGS command
#
# Example
#   ./sgs.py '{"command": "get_stb_settings", "receiver": "R0000000000-00", "cid": "1004", "name": "dish_ip_mode", "id": 63}'
#   ./sgs.py -i 192.168.1.24 '{"command": "get_stb_settings", "receiver": "R0000000000-00", "cid": "1004", "name": "dish_ip_mode", "id": 63}'

from sgs_lib import *
import argparse


# get params
parser = sgs_arg_parse(description="query any SGS command. May not set 'receiver' or 'cid' - default dev values are used if not set.")
parser.add_argument("query", help="actually SGS query. May not set 'receiver' and 'cid'")
args = parser.parse_args()

stb = STB(args)

query = args.query

data = stb.sgs_command(args.query)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  else:                        print ("Error, result =", str(result))
else:
  print (json.dumps(data, indent=2, separators=("","\t")))

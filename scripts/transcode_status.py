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
parser.add_argument("dvr_id", help="DVR ID")
parser.add_argument("rec_tm", help="DVRs recorded UTC time")
args = parser.parse_args()

stb = STB(args)

data = stb.sgs_command({"command":"transcode_event_status","dvr_id":args.dvr_id,"recorded_utc_time":args.rec_tm,"src":1,"type":1})
if not data:
   print ("error")
   quit()
result = data['result']
if result != 1:
   if "reason" in data.keys():  print ("Error status, \"" + data['reason'] + "\" result=" + str(result))
   else:                        print ("Error status, result =", str(result))
   quit()


if stb.verbose: print (json.dumps(data, indent=2))
print (data["transcode"]["status"])

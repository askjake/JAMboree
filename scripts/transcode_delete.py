#!/usr/bin/env python3

from sgs_lib import *
import argparse


# get params
parser = sgs_arg_parse(description="detelte transcoded files for specified DVR")
parser.add_argument("dvr_id", help="DVR ID")
parser.add_argument("rec_tm", help="DVRs recorded UTC time")
args = parser.parse_args()

stb = STB(args)

data = stb.sgs_command({"command":"transcode_delete","id":args.dvr_id,"recorded_utc_time":args.rec_tm,"src":1,"type":1})

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  else:                        print ("Error, result =", str(result))
else:
  print ("DVR sideloading files deleted")

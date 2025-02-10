#!/usr/bin/env python3

from sgs_lib import *
import argparse


# get params
parser = sgs_arg_parse(description="get sideloading transcode queue.")
args = parser.parse_args()

stb = STB(args)

data = stb.sgs_command({"command":"transcode_queue_v2","before":0,"after":0,"req_total_size":True})

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
   if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
   else:                        print ("Error, result =", str(result))
   quit()

if stb.verbose: print (json.dumps(data, indent=2))

print ("total in queue:", data["totalSize"])

for elem in data["dvr_list"]:
   line = "{:<3} {:<12}        {:<25} {}".format(elem["dvr_id"],elem["rec_tm"],elem["transcode"]["status"], elem["title"])
   if elem["transcode"]["status"] == "TRANSCODE_ACTIVE": line += "  ({}%)".format(elem["transcode"]["percent"])
   print (line)

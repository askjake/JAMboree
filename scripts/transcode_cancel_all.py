#!/usr/bin/env python3

from sgs_lib import *
import argparse
import time

# cancel transoded by DVR-ID / UTC-time
# return 1 on success
def transcode_cancel(stb, dvr_id, rec_tm):
   data = stb.sgs_command({"command":"transcode_cancel","id":dvr_id,"recorded_utc_time":rec_tm})
   if not data:
      print ("       error transcode_cancel")
      return 0
   result = data['result']
   if result != 1:
      if "reason" in data.keys():  print ("       Error transcode_cancel, \"" + data['reason'] + "\" result=" + str(result))
      else:                        print ("       Error transcode_cancel, result =", str(result))
   return data["result"]

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

for elem in reversed(data["dvr_list"]):
   print ( "cancel {:<3} {:<12}        {:<25} {}".format(elem["dvr_id"],elem["rec_tm"],elem["transcode"]["status"], elem["title"]))
   transcode_cancel(stb, elem["dvr_id"], elem["rec_tm"])
   time.sleep(1)


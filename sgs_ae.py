#!/usr/bin/env python3
#
# get AE
#
# Usage
#  ./sgs_ae.py receiver_id [ip]
#   where 
#      - receiver_id - id of receiver to get AE from
#      - ip - is STB IP
#
# Example
#   ./sgs_ae.py R1911705054-56
#   ./sgs_ae.py R1911705054-56 192.168.1.24
#
# Note, pairing code is available in logs:
#   # tail -F  /mnt/MISC_HD/esosal_log/stbCtrl/stbCtrl.0 |grep -e "Pairing code is"

from sgs_lib import *
import signal
import sys
import argparse

# Ctrl-C handler
def signal_handler(sig, frame):
   print('Exiting')
   exit()


# get params
parser = sgs_arg_parse(description="get Async events from receiver")
parser.add_argument("event", help="AE events to track, track all if not set", nargs='*')
args = parser.parse_args()

stb = STB(args)

TRACK_EVENTS = args.event

stb.attach()
if not stb.cid:
   print ("Cannot get CID...")
   quit()

if args.name: print (args.name)
print ("STB ", stb.stb)
print ("CID ", stb.cid)
print ("RECEIVER ", stb.rid)
print ("STB_IP ", stb.ip)
if args.event:
   print ("track only events: ", args.event)
print ()

# register handler for Ctrl-C
signal.signal(signal.SIGINT, signal_handler)

# go on main loop
querry = {"command": "async_events_xip_v2", "error": False, "ack_list": [], "cid_list": [65535, stb.cid], "poll_delay":10000, "receiver":stb.rid, "cid":stb.cid}
while True:
   data = stb.sgs_command(querry)

   if not data:
      print ("error")
      quit()

   result = data['result']
   if result != 1:
      print ("Error, \"" + data['reason'] + "\" result=" + str(result))
   else:
      events = next ((x for x in data['cid_list'] if x["cid"]==stb.cid), {"uc_list":{}})["uc_list"]
      
      querry["ack_list"] = []
      for cid_group in data["cid_list"]:
         ack_list = []
         for event in cid_group["uc_list"]:
            # form ack list for each AE event
            ack_list.append({"evt":event["evt"], "time":event["time"]})
            # print AE event info
            if (AE_EVENTS_NAMES[int(event["evt"])] in TRACK_EVENTS) or not TRACK_EVENTS: # TODO change to subscribe instead of filter
               print ("\ncid {:>5}, time {:<7}  event {:<3}  {}".format(
                  cid_group["cid"], event['time'], event["evt"], AE_EVENTS_NAMES[int(event["evt"])]))
               if "info" in event.keys():
                  print (json.dumps(event["info"], indent=2, separators=("","\t")))
         # form ack list for each cid
         querry["ack_list"].append({"cid":cid_group["cid"], "uc_list":ack_list})

      #querry["ack_list"] = [{"cid":stb.cid, "uc_list":ack_list}]

      #print ("---------------------")
      #print ("new cmd: ", json.dumps( querry ))

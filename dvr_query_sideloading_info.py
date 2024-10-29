#!/usr/bin/env python3

from sgs_lib import *
import argparse


# get params
parser = sgs_arg_parse(description="get DVRs with sideloading info")
parser.add_argument("-N", "--num", help="how many items to display", type=int, default=100)
args = parser.parse_args()

stb = STB(args)

# more about syntax for dvr_query_sideloading_info
# https://confluence.dtc.dish.corp/display/SGAPI/Sideloading+Commands#SideloadingCommands-dvr_query_sideloading_infoCommand
# type 1 - User recorded
# src  0x1 - internal HDD
# main_sort 9 - shortest first; 1 - by name
data = stb.sgs_command({"command":"dvr_query_sideloading_info","req_total_size":True,"order":1,"main_sort":9,"sub_sort":1,"before":0,"after":args.num,"include":True,"src":1,"type":1,"filter":0,"search_type":0,"evt":{"start_dvr_id":0,"rec_tm":0,"name":"","theme":0,"grp_id":0,"network_id":0}})

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
   if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
   else:                        print ("Error, result =", str(result))
   quit()

if stb.verbose: 
   print (json.dumps(data, indent=2))


print ("id      utc_tm   dur        status                name")
for item in data["dvr_list"]:
   print ("{:<3} {:<12} {:<6} {:<25} {}".format(item["dvr_info"]["dvr_id"],item["dvr_info"]["rec_tm"],item["dvr_info"]["duration"],
      item["transcode"]["status"],item["detail_evt"]["evt_info"]["title"],))

print ("total", data["total_size"])

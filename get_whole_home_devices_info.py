#!/usr/bin/env python3
#
# get info about connected STBs
#

from sgs_lib import *
import argparse

dev_type = {
0:  "Invalid",
1:  "XIP813",
2:  "XIP913",
3:  "XIP110",
4:  "XIP110CR",
5:  "XIP112",
6:  "XIP110W",
7:  "AP",
8:  "Inet Con",
9:  "UPnP DMS",
10: "ZIP110",
11: "ZIP1018",
12: "HEVC211",
13: "AP-2",
14: "ZIP110HEVC",
15: "XIP712",
16: "ATVMJ4",
17: "ATVWJ4",
18: "SNAP2",
}

# get params
parser = sgs_arg_parse(description="get connected devices info")
parser.add_argument("num", help="number of devices to display", nargs='?', default="10")
args = parser.parse_args()

stb = STB(args)

querry = {"command": "get_whole_home_devices_info", "cat_mask": 0, "type_mask": 0, "start_id": 0, "include": True, "size": args.num}

data = stb.sgs_command(querry)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  if 'reason' in data:
    print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  else:
    print ("Error, result="+str(result))
else:
  if stb.verbose: print (json.dumps(data, indent=2, separators=("","\t")))
  for elem in data['dev_list']:
    if elem["type"] not in dev_type.keys(): elem_type = "unknown"
    else:                                   elem_type = dev_type[elem["type"]]
    paired_hopper_str = ""
    if elem['stb_details']['paired_hopper']: 
      paired_hopper = next((x for x in data['dev_list'] if elem['stb_details']['paired_hopper']==x['stb_details']['receiver']), None)
      if paired_hopper: paired_hopper_str = "(paired to {}: {})".format(paired_hopper['id'], paired_hopper['name'])
    print ("{:<2} {:10} {:13}    {:13} {} {}".format(elem['id'], elem_type, elem['stb_details']['receiver'], elem['stb_details']['smartcard'], elem['name'], paired_hopper_str))


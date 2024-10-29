#!/usr/bin/env python3
#
# Gets STB auathorization keys
#

from sgs_lib import *
import argparse

keys = {
0x1: "VF-Test2 right is authorized.",
0x2: "commercial right is enabled.",
0x4: "Netflix right is enabled.",
0x8: "Netflix NTS test enabled.",
0x10: "Home automation enabled.",
0x20: "Soak UI is enabled.",
0x40: "Invidi is addressable to the commercial box.",
0x80: "DVR is disabled.",
0x100: "the STB has H6 authorization",
0x200: "the STB has the Adult control right set",
0x400: "Disable Sling streaming and transfers for selected channels.",
0x800: "Youtube right is enabled.",
0x2000: "MVDDS right is enabled.",
0x4000: "French VOD right is enabled.",
0x8000: "disable tuner 2 (HEVC211 only).",
0x10000: "disable sports app group.",
0x20000: "disable Entertainment/News/Weather Group.",
0x40000: "Amazon Prime right is enabled.",
0x80000: "Dish Communities app right is enabled.",
0x100000: "JOE (Joey Over Ethernet) UI is enabled"
}

# get params
parser = sgs_arg_parse(description="get STB authorization keys")
parser.add_argument("-R", "--rights", help="manually set rights value (will not make sgs requ in this case)", type=int)
args = parser.parse_args()

stb = STB(args)

if args.rights:
   rights = args.rights
   if stb.verbose: print ("check rights val", rights)
else:
   data = stb.sgs_command({"command":"query_ca_rights"})

   if not data:
      print ("error")
      quit()
   if not isinstance(data, dict):
      print("Unexpected data format received. Expected a dictionary.")
      quit()

   result = data['result']
   if result != 1:
     if    result == 36:            print ("Client is not authorized")
     elif 'reason' in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
     else:                          print ("error,", result)
     quit()

   rights = data['rights']

if stb.verbose: print ("rights = 0x{:x}:".format(rights))
for key in keys.keys():
   if (rights & key) != 0:
      if stb.verbose:
         print ("0x{:<6x} - {}".format(key, keys[key]))
      else:
         print (keys[key])


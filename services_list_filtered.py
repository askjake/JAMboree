#!/usr/bin/env python3
#
# Get service list filtered - same as guide on STB
#
# syntax
#   services_list_xip.py [-m minor] [-S svc] [keyword]
#     - major - print only major ID of displayeble channel
#     - svc   - print only service ID
#     - keyword - substring to look in displayeble channel number or service name
#

from sgs_lib import *
import argparse


def stype_str (stype):
   types = {
         0: 'sat',
         1: 'VOD',
         2: 'grp',
         3: 'int',
         4: 'ota',
         5: 'ip '}
   if stype in types:
      return types[stype]
   else:
      return '-?-'

def vtype_str (vtype):
   types = {
         0: ' -     ',
         1: 'SD     ',
         2: 'HD     ',
         3: '1080P  ',
         4: '3D     ',
         5: '4KHD   ',
         6: '4KHDR10'}
   if vtype in types:
      return types[vtype]
   else:
      return ' -     '

# get params
parser = sgs_arg_parse(description="get services list")
# type - see https://confluence.dtc.dish.corp/display/SGAPI/Important+Definitions#ImportantDefinitions-ServicesListType
parser.add_argument("-T", "--type",    help="[1] services type: 1 all;  2 subscribed, 3 subscribed non-sd, 4 ota, 5 locked, 6 fav1, 7 fav2, 8 fav3, 9 fav4, 10 unsubscribed", type=int, default=1)
parser.add_argument("-D", "--downmap", help="[2] downmap prefs: 0 use stb prefs, 1 hd only, 2 hd and sd", type=int, default=2)
parser.add_argument("-V", "--vod", help="[1] vod prefs: 0 all, 1 one vod per channel, 2 no vod", type=int, default=1)
args = parser.parse_args()

stb = STB(args)


# get list of all channels with names and flags
data = stb.sgs_command({"command":"services_list_xip","start_svc":0,"req_total_size":"true","size":0})

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  else:                        print ("Error, result =", str(result))
  quit()

list_all = data["svc_list"]


# get sorted and ordered list
data = stb.sgs_command({"command":"services_list_filtered","adult":1,"attr":7,"chnl_order":1,"downmap":args.downmap,"locked":1,"type":args.type,"vod":args.vod,"exclude":0})

if not data:
    print ("error")
    quit()

result = data['result']
if result != 1:
   if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
   else:                        print ("Error, result =", str(result))
   quit()


if stb.verbose:
   print ()
   print ("services_list_xip return:")
   print (json.dumps(list_all, indent=2, separators=("","\t")))
   print ()
   print ("services_list_filtered return:")
   print (json.dumps(data["svc_id_info_list"], indent=2, separators=("","\t")))
   print ()

# print filtered/sorted list using info from list_all
print ("svc ID    [ psvc  /persistent_svc] type         name")
nerror=0
for elem in data["svc_id_info_list"]:
   channel = next((x for x in list_all if elem["svc"]==x["svc"]), None)
   if channel == None:
      print ("???       [{:6} / {:12}]".format(elem["svc"], elem["psvc"]))
      continue
   logline = "{:<9} [{:6} / {:12} ] {},{}, {}".format(
      channel['disp_ch'], 
      elem["svc"],
      elem["psvc"],
      stype_str(channel['stype']),
      vtype_str(channel['vtype']),
      channel['svc_name']
      )
   if elem["psvc"] != channel["persistent_svc"]:
      logline += "      ---------------- psvc mismatch {}".format(channel["persistent_svc"])
      nerror += 1
   print (logline)

print()
print("{} total services".format(len(data["svc_id_info_list"])))
if nerror != 0: print (nerror, "psvc/persistent_svc mismatch")

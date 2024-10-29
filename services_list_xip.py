#!/usr/bin/env python3
#
# Get service list
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
parser.add_argument("-N", "--num", help="how many items to display", type=int, default=0)
parser.add_argument("-m", "--major", help="filter by Major ID", type=int)
parser.add_argument("-S", "--svc", help="filter by service id", type=int)
parser.add_argument("keyword", help="the keyword to search in displayeble chan num or channel name", nargs='?', default="")
args = parser.parse_args()

stb = STB(args)


querry = {"command":"services_list_xip","start_svc":0,"req_total_size":"true","size":args.num}
#querry = {"command":"services_list_filtered","adult":1,"attr":7,"chnl_order":1,"downmap":2,"locked":1,"type":1,"vod":1,"exclude":0}

data = stb.sgs_command(querry)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  if "reason" in data.keys():  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  else:                        print ("Error, result =", str(result))
  quit()


if stb.verbose:
  #print (json.dumps(data, indent=2, separators=("","\t")))
  print()
  if args.major: print ("look for major ", args.major)
  if args.svc: print ("look for svc ", args.svc)
  print()

i=0
for element in data["svc_list"]:
   if ((not args.major) and (not args.keyword) and (not args.svc)) or \
      args.keyword in element['disp_ch'] or \
      args.keyword in element['svc_name'] or \
      element['major'] == args.major or \
      element['svc']   == args.svc:
         i+=1
         if stb.verbose:
            print (json.dumps(element, indent=2, separators=("","\t")))
         else:
            print ("{:<9} {:7} {},{}, {}".format(
               element['disp_ch'], 
               "("+str(element['svc'])+")",
               stype_str(element['stype']),
               vtype_str(element['vtype']),
               element['svc_name']
               ))
print()
print ("found", i, "of", len(data["svc_list"]), "elements")

#!/usr/bin/env python3
#
# execute SGS command
#
# Usage
#  ./get_tuner_usage_v2.py [-i IP]
#   where 
#      - IP - is STB IP
#
#
# https://confluence.dtc.dish.corp/pages/viewpage.action?pageId=113606854#ChannelChange/LandingPage-tuner_usage_information
#

from sgs_lib import *
import argparse

def tuner_type (tuner_id):
   types = {
         0: 'inval    ',
         1: 'sat      ',
         2: 'offair   ',
         3: 'rem sat  ',
         4: 'broadband' }
   if tuner_id in types:
      return types[tuner_id]
   else:
      return 'unknown  '
   
def usage_type (usage_id):
   types = {
         0:  'free',
         1:  'TV+',
         2:  'TV-',
         3:  'slin+',
         4:  'PTAT-',
         5:  'EPG-',
         6:  'RMS-',
         7:  'swDw-',
         8:  'chSw-',
         9:  'Acq-',
         10: 'PTATw1',
         11: 'PTATw2',
         12: 'OFFsc-',
         13: 'bgsr',
         14: 'bgsnr'
         }
   if usage_id in types:
      return types[usage_id]
   else:
      return 'unknown  '
   
def status_str (status_id):
   types = {
         -1: 'inval',
         0:  'locked',
         1:  'lost',
         2:  'acq',
         3:  'RainFaid',
         4:  'SptBm Err',
         5:  'SptBm los',
         6:  'PatPmt er',
         6:  'stream er',
         }
   if status_id in types:
      return types[status_id]
   else:
      return 'unknown  '
   

def attr_str (attr):
   str = ""
   if attr & 0x0001 : str+=" rec"
   if attr & 0x0002 : str+=" pause"
   if attr & 0x0004 : str+=" PIP"
   if attr & 0x0008 : str+=" owner"
   if attr & 0x0010 : str+=" sharing"
   if attr & 0x0020 : str+=" avail"
   if attr & 0x0040 : str+=" PTAT"
   if attr & 0x0080 : str+=" dPIP"
   if attr & 0x0100 : str+=" PIPact"
   if attr & 0x0200 : str+=" bgAV"
   if attr & 0x0400 : str+=" mPIP"
   if attr & 0x0800 : str+=" pred"
   if attr & 0x1000 : str+=" AV"
   return str
# get params
parser = sgs_arg_parse(description="get current tuners usage by get_tuner_usage_v2 SGS command")
args = parser.parse_args()

stb = STB(args)

querry = {"command": "get_tuner_usage_v2"}

data = stb.sgs_command(querry)

print("Returned data:", data)  # Debug print to see the structure of returned data

if not data:
   print ("error")
   quit()

if not isinstance(data, dict):
   print("Error: data is not a dictionary")
   quit()

result = data.get('result')
if result != 1:
  print ("Error, \"" + data.get('reason', 'Unknown reason') + "\" result=" + str(result))
  quit()

if stb.verbose:
  print (json.dumps(data, indent=2, separators=("","\t")))
  print()

tuners = data['tuner_usage_list']

for tuner in tuners:
   if tuner['usage'] == 0: continue
   print ("tuner {:<2} type {} usage {:<6}   status {:<9} ({:9})   by (cid {:>4}) {:<15}  [{}] {}".format(
      tuner['tuner'], 
      tuner_type(tuner['tuner_type']),
      usage_type(tuner['usage']), 
      status_str(tuner['status']),
      attr_str(tuner['attr']),
      tuner['cid'], 
      tuner['name'], 
      tuner['svc'], 
      tuner['title'], 
      ))

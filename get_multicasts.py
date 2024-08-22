#!/usr/bin/env python3
#
# returns list of multicasts currently used by STB
#
# Usage
#  ./get_multicasts.py [-i ip]
#   where 
#      - ip - is STB IP
#
# Example
#   ./get_multicasts.py -i 192.168.1.20

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

def get_descr(pid, net_id="0"):
   if (type(pid) is int):
      pid = "{:>04x}".format(pid)
   lookup = [ \
      ("0000",   "PAT",    "Program Association Table"), \
      ("0001",   "CAT",    "Conditional Access Table"), \
      ("000x",   "?",      "?"), \
      ("0010",   "NIT",    "Network Information Table"), \
      ("0011",   "SDT",    "Service Descriptor Table"), \
      ("0012",   "EIT",    "Event Information Table"), \
      ("0014",   "TDT",    "Time Data Table"), \
      ("0018",   "PGT",    "Program Guide Table"), \
      ("0019",   "SST",    "Status Stream Table"), \
      ("001x",   "?",      "?"), \
      ("0020",   "?",      "?"), \
      ("0021",   "PMT",    "Program Map Table"), \
      ("00xx",   "ECM",    "Entitlement Control Message"), \
      ("0120",   "EMM",    "Entitlement Management Message"), \
      ("0121",   "?",      "?"), \
      ("01xx",   "ECM",    "Entitlement Control Message"), \
      ("050x",   "?",      "?"), \
      ("051x",   "?",      "?"), \
      ("0520",   "?",      "?"), \
      ("0521",   "?",      "?"), \
      ("05xx",   "ECM",    "Entitlement Control Message"), \
      ("02xx",   "APP",    "STB Applications"), \
      ("0300",   "EEPG",   "Extended Electronic Program"), \
      ("0301",   "EEPG",   "Extended Electronic Program"), \
      ("0310",   "MTDTA",  "Metadata PID"), \
      ("0314",   "MTDTA",  "Metadata PID"), \
      ("0315",   "MTDTA",  "Metadata PID"), \
      ("0316",   "MTDTA",  "Metadata PID"), \
      ("0318",   "MTDTA",  "Metadata PID"), \
      ("0320",   "MTDTA",  "Metadata PID"), \
      ("0322",   "MTDTA",  "Metadata PID"), \
      ("0350",   "PEMM",   "Patch Entitlement Management Message"), \
      ("0351",   "PEMM",   "Patch Entitlement Management Message"), \
      ("0352",   "PEMM",   "Patch Entitlement Management Message"), \
      ("0355",   "PEMM",   "Patch Entitlement Management Message"), \
      ("0356",   "PEMM",   "Patch Entitlement Management Message"), \
      ("08xx",   "DWLD",   "Download PID"), \
      ("0907",   "ANNSTR", "Announcment Stream"), \
      ("090b",   "DLRTR",  "Dealer Tricle"), \
      ("0909",   "FVOD",   "Forced Video On Demand"), \
      ("090A",   "FVOD",   "Forced Video On Demand"), \
      ("0930",   "HERMES", "Hermes"), \
      ("10xx",   "AUD-o",  "Audio Only Service"), \
      ("11xx",   "AUD-o",  "Audio Only Service"), \
      ("1x22",   "VID",    "Video"), \
      ("1x23",   "AUD-1",  "Audio 1"), \
      ("1x24",   "AUD-2",  "Audio 2"), \
      ("1025",   "DPI",    "DPI"), \
      ("1x27",   "INVIDI", "INVIDI Break"), \
      ("1x28",   "INVIDI", "INVIDI Break"), \
      ("1x32",   "VID",    "Video"), \
      ("1x33",   "AUD-1",  "Audio 1"), \
      ("1x34",   "AUD-2",  "Audio 2"), \
      ("1035",   "DPI",    "DPI"), \
      ("1x37",   "INVIDI", "INVIDI Break"), \
      ("1x38",   "INVIDI", "INVIDI Break"), \
      ("17xx",   "ALB",    "Album Art"), \
      ("1Axx",   "TITLE",  "Title Data"), \
      ("1FFF",   "NULL",   "NULL PID") \
   ]
   
   # first check if it is OTA
   # all OTA PIDs has network ID 0xFF, we do not know OTA PIDs description so just return 'ota'
   if int(net_id)&0xFF00 == 0xFF00: return "ota", "Over The Air PID"

   for item in lookup:
      found = False
      for pattern, check in zip(item[0], pid):
         found=True
         if pattern!="x" and pattern!=check:
            found=False
            break
      if found: return item[1], item[2]
   return "?", "?"

statuses = "unknown", "OK", "R err", "W err", "Conn Lost", "closed", "zombie"


global tuner_list


# get params
parser = sgs_arg_parse(description="get opened multicasts list")
args = parser.parse_args()

stb = STB(args)

querry = '{"command":"dish_ip_get_opened_multicasts"}'

data, _  = stb.sgs_command(querry)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
   print ("Error, \"result\" = " + str(result))
   if "reason" in data.keys(): print (" result=" + str(result))
   quit()


if "tuners" not in data.keys():
   print ("No opened multicasts")
   quit()

tuner_list = data['tuners']

# now get tuner usage
data_tuner_usage, _ = stb.sgs_command('{"command":"get_tuner_usage_v2"}')

if not data_tuner_usage:
   print ("error")
   quit()

result = data_tuner_usage['result']
if result != 1:
   print ("Error, \"result\" = " + str(result))
   if "reason" in data_tuner_usage.keys(): print (" result=" + str(result))
   quit()


tuners_usage = data_tuner_usage['tuner_usage_list']

for tuner in tuner_list:
   print ("Tuner " + str(tuner['tuner_id']) + "  ts_id " + str(tuner['transport_id']) + "  net_id " + str(tuner['network_id']))
   this_tuner = next ((x for x in tuners_usage if x['tuner']==tuner['tuner_id']), None)
   if this_tuner is not None:
      print (" type {} usage {:<6}   status {:<9} ({:9})   by (cid {:>4}) {:<15}  [{}] {}".format(
         tuner_type(this_tuner['tuner_type']),
         usage_type(this_tuner['usage']), 
         status_str(this_tuner['status']),
         attr_str(this_tuner['attr']),
         this_tuner['cid'], 
         this_tuner['name'], 
         this_tuner['svc'], 
         this_tuner['title'], 
         ))
   for feeder in tuner['multicasts']:
      pid = feeder['pid']
      #print ("    " + str(pid).rjust(5) + (" (" + str(hex(pid)) + ")").ljust(9) + ":  " \
      #      + feeder['address'].rjust(13) + ":" + str(feeder['port']).ljust(5) + "  - (" + str(feeder['status']) + ") " + str(statuses[feeder['status']]))
      print ("    {:>5} (0x{:>04x}) {:<6} :  {:>15}:{:<5}  - ({}) {}".format(pid, \
         pid, \
         get_descr(pid,tuner['network_id'])[0], \
         feeder['address'], feeder['port'], feeder['status'], str(statuses[feeder['status']])))
   print ()

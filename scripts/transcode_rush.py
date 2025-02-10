#!/usr/bin/env python3

from sgs_lib import *
import argparse
import time


# get params
parser = sgs_arg_parse(description="generate transcode activity through all available DVRs")
parser.add_argument("num", help="how many transcodes to perform (defaults - forever)", type=int, default=-1, nargs='?')
parser.add_argument("-T", "--timeout", help="transcode timeout before cancel", type=int, default=5*60)
args = parser.parse_args()

stb = STB(args)


# transode DVR by DVR-ID / UTC-time
# return 1 on success
def transcode(stb, dvr_id, rec_tm):
   data = stb.sgs_command({"command":"transcode","id":dvr_id,"recorded_utc_time":rec_tm})
   if not data:
      print ("       error transcode")
      return 0
   result = data['result']
   if result != 1:
      if "reason" in data.keys():  print ("       Error transcode, \"" + data['reason'] + "\" result=" + str(result))
      else:                        print ("       Error transcode, result =", str(result))
   return data["result"]

# delete transoded files by DVR by DVR-ID / UTC-time
# return 1 on success
def transcode_delete(stb, dvr_id, rec_tm):
   data = stb.sgs_command({"command":"transcode_delete","id":dvr_id,"recorded_utc_time":rec_tm,"src":1,"type":1})
   if not data:
      print ("       error transcode_delete")
      return 0
   result = data['result']
   if result != 1:
      if "reason" in data.keys():  print ("       Error transcode_delete, \"" + data['reason'] + "\" result=" + str(result))
      else:                        print ("       Error transcode_delete, result =", str(result))
   return data["result"]

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

# get transode status for specified DVR-ID / UTC-time
# return status string (see 'transcode'->'status' https://confluence.dtc.dish.corp/display/SGAPI/Sideloading+Commands#SideloadingCommands-dvr_query_sideloading_infoCommand )
def transcode_event_status(stb, dvr_id, rec_tm):
   data = stb.sgs_command({"command":"transcode_event_status","dvr_id":dvr_id,"recorded_utc_time":rec_tm,"src":1,"type":1})
   if not data:
      print ("       error status")
      return "TRANSCODE_UNKNOWN"
   result = data['result']
   if result != 1:
      if "reason" in data.keys():  print ("       Error status, \"" + data['reason'] + "\" result=" + str(result))
      else:                        print ("       Error status, result =", str(result))
      return "TRANSCODE_UNKNOWN"
   return data["transcode"]["status"]


# get list of DVRs
# more about syntax for dvr_query_sideloading_info
# https://confluence.dtc.dish.corp/display/SGAPI/Sideloading+Commands#SideloadingCommands-dvr_query_sideloading_infoCommand
# type 1 - User recorded
# src  0x1 - internal HDD
# main_sort 9 - shortest first; 1 - by name
data = stb.sgs_command({"command":"dvr_query_sideloading_info","req_total_size":True,"order":1,"main_sort":9,"sub_sort":1,"before":0,"after":100,"include":True,"src":1,"type":1,"filter":0,"search_type":0,"evt":{"start_dvr_id":0,"rec_tm":0,"name":"","theme":0,"grp_id":0,"network_id":0}})

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

print ("total DVRs:", data["total_size"])

cnt = args.num

# loop got for 'cnt' transcodes (or endless if '-1')
while cnt != 0: # -1 forever, or downcounter till 0
   for item in data["dvr_list"]:
      if cnt == 0: break # finish transcode if reach 0 or till -1
      cnt -= 1

      # log current item
      dvr_id = item["dvr_info"]["dvr_id"]
      rec_tm = item["dvr_info"]["rec_tm"]
      print ("Transcdoe  dvr_id: {:<3}  utc_time: {:<12}   duration {:<6}  name: {}".format(
         dvr_id, rec_tm, item["dvr_info"]["duration"],
         item["detail_evt"]["evt_info"]["title"]))

      # delete transcoding if it is not 'none'
      status = transcode_event_status(stb, dvr_id, rec_tm)
      if "TRANSCODE_NONE" != status:
         print ("   cur status {},  delete before new transcode".format(status))
         transcode_delete(stb, dvr_id, rec_tm)
      # now recheck if deleted, skip if any error
      status = transcode_event_status(stb, dvr_id, rec_tm)
      if "TRANSCODE_NONE" != status:
         print ("   status after delete {}, something wrong with this DVR, skip it".format(status))
         continue

      # actually transcode request
      if 1 != transcode(stb, dvr_id, rec_tm):
         print ("   fail request transcode, skip it".format(status))
         continue

      # wait for 5 minutes with recheck transcode status each 5 seconds
      #   if transcode pass - report and delete transcode
      #   if does not complete during timeout - cancel transcode
      tm = args.timeout
      while tm>0:
         time.sleep(5)
         tm -= 5
         status = transcode_event_status(stb, dvr_id, rec_tm)
         if "TRANSCODE_COMPLETE" == status:
            print ("   transcode completed successfully. now delete")
            transcode_delete(stb, dvr_id, rec_tm)
            break
      if "TRANSCODE_COMPLETE" != status:
         print ("   transcode Not completed. Interrupt it")
         transcode_cancel(stb, dvr_id, rec_tm)


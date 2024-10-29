#!/usr/bin/env python3
#
# Gets autosuggest (when enter search screen)
#
# syntax
#   get_auto_suggestion.py [-d event_id] [keyword]
#     - event_id - specify currently watching event ID
#     - keyword  - the keyword to search for suggestions
#

from sgs_lib import *
import argparse

# get params
parser = sgs_arg_parse(description="get auto suggestions - most popular search by a word")
parser.add_argument("-d", "--id", help="evt_id_str to search")
parser.add_argument("keyword", help="the keyword to search", nargs='?', default="")
args = parser.parse_args()

stb = STB(args)

#querry = {"command":"get_auto_suggestion","evt_id_str":args.keyword,"filter_tree":{"compound_and":[{"scope":["DVR","PTAT","ARCHIVE","EPG","IPVOD","FVOD","ADVANCE_PLANNER","THEATER","DELETED","UNAVAILABLE"]}]}}
querry = {"command":"get_auto_suggestion","filter_tree":{"compound_and":[{"scope":["DVR","PTAT","ARCHIVE","EPG","IPVOD","FVOD","ADVANCE_PLANNER","THEATER","DELETED","UNAVAILABLE"]}]}}
if args.keyword:
   querry['query_str'] = args.keyword
if args.id:
   querry['evt_id_str'] = args.id

#print (json.dumps(querry, indent=2, separators=("","\t")))
#quit()

data = stb.sgs_command(querry)

if not data:
   print ("error")
   quit()

result = data['result']
if result != 1:
  print ("Error, \"" + data['reason'] + "\" result=" + str(result))
  quit()


i=0
for element in data["auto_suggest"]:
   print ("{:2} type: {:<15} id: {:<15} title: {:<20}".format(
      i,
      element['group'], 
      element['id_type_list'][0]['id'],
      element['title']))
   i+=1

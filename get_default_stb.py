#!/usr/bin/env python3
#
# prints default STB info
#

from sgs_lib import *
import argparse


# get params
parser = argparse.ArgumentParser(description="prints default STB")
parser.add_argument("-n", "--name", help="print STB name", action="store_true")
parser.add_argument("-i", "--ip", help="print STB IP", action="store_true")
parser.add_argument("-s", "--stb", help="print STB Receiver ID", action="store_true")
args = parser.parse_args()

stb = STB()
if not args.name and not args.ip and not args.stb:
   # by default prints all info
   print (stb)
else:
   if args.name: print (stb.name)
   if args.ip:   print (stb.ip)
   if args.stb:  print (stb.stb)

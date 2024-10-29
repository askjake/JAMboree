#!/usr/bin/env python3
#
# get STB information
#

from sgs_lib import *
import argparse


# get params
parser = sgs_arg_parse(description="get STB information")
parser.add_argument("id", nargs='?', default=6, type=int, choices=range(1,12),
      help =
 '''
 data group id (defaults to 6)
 ID values:
  - 1 ptat_authorized_local_services
  - 2 backup_date
  - 3 smartcard_callout_date
  - 4 contact_information
  - 5 receiver_smartcard
  - 6 system_information (default)
  - 7 sling_information
  - 8 sys_sw_information
  - 9 preference_res
  - 10 hdd_diagnostics
  - 11 mmc_nand_wear_status
 ''')
args = parser.parse_args()

stb = STB(args)

# Fetch STB information
try:
    result_data, receiver = stb.sgs_command({"command": "get_stb_information", "id": args.id})
    if not result_data:
        print("Error: No data returned")
        quit()

    result = result_data.get('result')
    if result != 1:
        reason = result_data.get('reason', 'Unknown')
        print(f"Error: {reason}, result={result}")
        quit()

    if args.id == 6 and not stb.verbose:
        print(f"{stb.name}:")
        print(f"rxid         : {result_data['data'].get('rxid', 'N/A')}")
        print(f"smartcard_id : {result_data['data'].get('smartcard_id', 'N/A')}")
        print(f"hwid         : {result_data['data'].get('hwid', 'N/A')}")
        print(f"model        : {result_data['data'].get('model', 'N/A')}")
        print(f"sw_ver       : {result_data['data'].get('sw_ver', 'N/A')}")
    else:
        print(json.dumps(result_data, indent=2, separators=(",", ": ")))

except Exception as e:
    print(f"An error occurred: {str(e)}")
    quit()
# https://git.dtc.dish.corp/montjac/JAMboree.git
# git@git.dtc.dish.corp:montjac/JAMboree.git

# API Calls to JAMboree
  1. http://localhost:5001/55/<remote>/<button_id>/<delay>	
  2. http://localhost:5001/55/<remote>/<button_id>
  3. http://localhost:5001/rf/<remote>/<stb_name>/<button_id>/<delay>/
  4. http://localhost:5001/sgs/<remote>/<stb_name>/<button_id>/<delay>/
  5. http://localhost:5001/triggered/<date>/<machine_name>/<stb_name>/<category_id>/<event_id>

Web GUI available to control settops from a browser at <pc-ip:5001>
  A server is started up at localhost:5001
  
download the zip file and unzip to the location of your choice. *I recomend making a new folder: Domuments/JAMboree/ then saving the unzipped files in there.

# To start JAMboree,
  Windows:
    In your folder with all the files, run 'BOOM.bat' *You can double click it or run from cmdln 
    
    The first time it opens, you will need to select a COM port and click refresh.
    Make sure to 'save' before you close.
    
  Linux:
    Start BOOM.sh and install dependencies as the come up. *future will include its own BOOT file.

# The gui that is where settings are done:
It should display your computers name at the top. 
5/16/2024 *added column for Master STB.  that is the hopper for a joey
for any stb, select a Master STB and sgs commands will be directed through that hopper
  1. Serial COM port
  2. STB Names
  3. STB RxID's
  4. STB IP's
  5. Remote Protocols to use
  6. SGS pairing
  7. SGS jump box 
  8. Main Hopper

# Debug menu
The following buttons are within:
  1. Upload: requests logs be uploaded for selected boxs and saves request ID's in upload_result.json
    the default file it collects is nal_0.cur
  2. Uploadable Files: This gathers a list of files available from boxs and saves it in uploadable_files.json
  4. Uploadable file groups: You guessed it, This gathers a list of file groups available and saves it in uploadable_file_groups.json
    * FUTURE: this will be used to link filename to file id and referenced when Device Partner detects a failed test. 
    * A table needs to be made to link what is being tested to what files are relevent.
We now have a list of uploadable files displayed on the right. Selct the logs you want and 'Request Log Upload'
Download Tab: lists your settops if they have logs in cc_share.
  Select the settop(s) for which you want logs
  Click 'download logs' and JAMboree will download and unzip your logs for you.
  (in the future, our chatbot will read and ingest logs from here)

# Check Channel Button
Press it and you will see the programs each tuner is tuned to.
Tuners with active programing are displayed
Now that JAMboree can ask the settop what its watching, that information can be leveraged against what is expected during automated tests.
Latest updates are stored in:
	'scripts/channel_check.txt'

# Multicasts Button
	This Channel Check and displays multicast IPs for DishIP.

# SGS find button.
It scans network for dev boxs and updates the ip if it has changed.
It will add new found settops to the bottom line.
You can tell it which rf remote it is by puting a number in the box on the right and press enter.

# Get Logs Button
This button triggers the collection of dev logs from any unsecurred settops selected.
They are currently set to be stored in "diship@{Linux_pc}/stbmnt/smplogs/{RxId}/{date}"


# Remote Control Buttons are held for as long as you press it.
I made some advancements in converting sgs commands. Like when you hold 'Home' for longer than a second, it is converted to 'Sys Info'

# To use RF remote, 
select the comport.
If you dont see your com-port, click the 'refresh' button <top-left>
Com-port is common to all  

# To use SGS, 
  RxId needs all 12 numbers, that means R1234567890-12
  Your PC needs to be able to ping the IP in STB diagnostics
  *Or SSH access to a computer that is able to ping the IP is STB diagnostics
    Put the IP of that computer at the bottom in "Linux Jump Box IP"
    and SSH username
    the first time you will need to enter your password in the command line that opened along side the gui.
  If you pc is not on the same network as the STB IP, it will automatically try to go through "Linux JumpBox IP"
  
# Select a COM port for each remote
	Sometimes you will have more than 1 DART system and need to differentiate them.
	Select the COM port for that specific remote and it will remember which DART to use for that STB name.
	
# Linuc_pc for each remote/stb
	Select or enter the IP of your linux pc you want to use as an SSH jump box 
	Linux_pc is automatically used when your stb is on a different network from yours. 
	
# SGS commands on Joey's
	select the host hopper in the column "Master STB". It will update the database.
	Now sgs commands to that joey will automaticaly route through the host hopper.
To find a Joey's host hopper, look in 'Sys Info' then (4)Whole Home. When 'link status' is 'linked', you are linked. That is the hopper you need to select in 'Master STB'. All pairing attempts go to the hopper. So you have to get the pin from the hopper.
	
curl -v -X POST -d "{\"command\":\"remote_key\",\"receiver\":\"R1911704405-24\",\"stb\":\"R1971325219-40\",\"tv_id\":0,\"key_name\":\"Guide\"}" http://192.168.1.19:8080/www/sgs

reciever is the hopper
stb is the joey
ip is the hopper

IN OTHER WORDS

Only hoppers can get SGS commands, so send the command to the hopper and tell it which RXID you want to control.
In this case 
	  
# Example: 
for ZiP1018-9
 R1911704405-24
 192.168.1.19,
ATV MJ4-11
 R1971325219-40,
ATV WJ4-14
 R1971323654-59
Send 'guide' to ZiP1018-9
	curl -v -X POST -d "{\"command\":\"remote_key\",\"receiver\":\"R1911704405-24\",\"stb\":\"R1911704405-24\",\"tv_id\":0,\"key_name\":\"Guide\"}" http://192.168.1.19:8080/www/sgs

Send 'guide' to ATV MJ4-11	
	curl -v -X POST -d "{\"command\":\"remote_key\",\"receiver\":\"R1911704405-24\",\"stb\":\"R1971325219-40\",\"tv_id\":0,\"key_name\":\"Guide\"}" http://192.168.1.19:8080/www/sgs
	
Send 'guide' to ATV MJ4-14	
	curl -v -X POST -d "{\"command\":\"remote_key\",\"receiver\":\"R1911704405-24\",\"stb\":\"R1971323654-59\",\"tv_id\":0,\"key_name\":\"Guide\"}" http://192.168.1.19:8080/www/sgs

# To use SGS with SECURED settop 
  it will first need to be paired to your computer.
This will create a username/password compination and save it in scripts/base.txt
  Select a single settop
  Click the "SGS Pair" button <bottom-right>
  In the little text window at the bottom, Enter the PIN displayed on the tv screen
  Click "Submit PIN"

curl commands to it look like this:
/55/"remote"/"button_id"

  EXAMPLE:
/55/1/home
  working backwords,
this will send a home
  to remote #1
    with the rf remote

/sgs/4/8
  working backwords,
this will send "8"
  to settop #4
    via DAny sgs command

	
	
##Notes
Button presses are designed to relect human interaction. SGS commands are unique to the command, not the button. So I put an interpreter in commands.py
	this is where long pressing, or holding a button changes the function.
def get_sgs_codes(button_id, delay):
    if button_id == 'Home' and delay >= 1000:
        button_id = 'Sys Info'
    elif button_id == 'Back' and delay >= 1000:
        button_id = 'Live TV'
    elif button_id == 'ddiamond':
        button_id = 'PiP Toggle'
    elif button_id == 'FWD':
        if delay >= 1000:
            button_id = 'Fast Forward'
    elif button_id == 'RWD':
        if delay >= 1000:
            button_id = 'Rewind'

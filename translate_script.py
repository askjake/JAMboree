import sys
import os

def remove_lines(input_file):
    lines = []
    with open(input_file, 'r') as infile:
        lines = infile.readlines()

    output_lines = []
    skip = False
    for i in range(len(lines)):
        if "20829" in lines[i]:
            if i + 1 < len(lines) and "20848" in lines[i + 1]:
                skip = True
            else:
                skip = False
        if not skip:
            output_lines.append(lines[i])

    return output_lines
    
def time_lines(input_file):
    lines = []
    with open(input_file, 'r') as infile:
        lines = infile.readlines()

    output_lines = []
    next_timestamp = None
    for i in range(len(lines)):
        parts = lines[i].strip().split(',')
        if len(parts) > 1 and parts[1] == '20829':
            if next_timestamp is not None:
                current_timestamp = int(parts[0])
                time_diff = current_timestamp - next_timestamp
                parts[0] = str(time_diff)
                output_lines.append(','.join(parts) + '\n')
            next_timestamp = int(parts[0])
        else:
            output_lines.append(lines[i])

    return output_lines

def add_dividers(lines):
    output_lines = []
    for i, line in enumerate(lines):
        if i > 0 and i % 100 == 0:
            output_lines.append('----splits-ville--------')
        output_lines.append(line)
    return output_lines


def translate_file(input_file):
    output_file = f"{os.path.splitext(input_file)[0]}_translated{os.path.splitext(input_file)[1]}"

    try:
        # Remove lines and add dividers
        #lines = remove_lines(input_file)
        lines = time_lines(input_file)
        lines = add_dividers(lines)

        with open(output_file, 'w') as outfile:
            for line in lines:
                parts = line.strip().split(',')
                if len(parts) > 1:
                    try:
                        # Translate the second number using the lookup dictionary
                        key = int(parts[1])
                        if key in lookup:
                            parts[1] = lookup[key]
                        else:
                            parts[1] = f"Unknown({parts[1]})"  # Mark unknown keys
                    except ValueError:
                        parts[1] = f"Invalid({parts[1]})"  # Handle non-integer values
                    stripped_parts = parts[:2]
                    outfile.write(','.join(stripped_parts) + '\n')
                else:
                    # In case the line has less than 2 parts, write it as is (or handle it as needed)
                    outfile.write(line + '\n')

        return output_file

    except Exception as e:
        return f"An error occurred: {e}"

        
lookup = {
  105:"Power Toggle",
  20830:"Power Home",
  103:"Power On",
  104:"Power Off",
  20600:"SAT",
  20601:"TV",
  20606:"DVD",
  20602:"AUX",
  253:"Enter",
  250:"Cancel",
  642:"Guide",
  136:"Menu",
  651:"DVR",
  424:"Search",
  20658:"Keypad",
  20707:"Pause/Play",
  80:"Rewind",
  70:"Fast Forward",
  86:"Stop",
  428:"Skip Back",
  429:"Step Forward",
  20665:"Format",
  20544:"System Wizard",
  20710:"Input",
  20547:"Recover",
  2:"0",
  3:"1",
  4:"2",
  5:"3",
  6:"4",
  7:"5",
  8:"6",
  9:"7",
  10:"8",
  11:"9",
  20659:"* Enter",
  20660:"# Enter",
  20850:"* Hold",
  20851:"# Hold",
  65535:"DEPRECATED",
  38:"Page Down",
  37:"Page Up",
  72:"Pause",
  74:"Play",
  77:"Record",
  101:"Blue",
  102:"Green",
  106:"Red",
  111:"Yellow",
  121:"Left",
  122:"Right",
  123:"Up",
  120:"Down",
  256:"Info",
  643:"Live TV",
  20669:"Jump",
  56:"Recall",
  318:"PiP Toggle",
  20656:"PiP Position",
  317:"PiP Swap",
  20657:"DISH",
  20829:"Press & Hold",
  20816:"Back",
  36:"Home",
  20668:"Info Toggle",
  20817:"Options",
  20818:"Applications",
  20820:"User Config",
  20826:"User Hold",
  20848:"User Config1",
  20849:"User Hold1",
  20827:"User Config2",
  20828:"User Hold2",
  255:"Help",
  20832:"Microphone",
  20822:"ABC Toggle",
  20823:"123 Toggle",
  20819:"Back Space",
  20821:"Enter",
  20853:"Back Space Hold",
  20852:"Enter Hold",
  20680:"XY Point",
  20687:"Multi XY Point",
  20678:"Thumb Up",
  55:"Channel Up",
  54:"Channel Down",
  20838:"Mic Pressed",
  20835:"Mic Done",
  20482:"TV Power Toggle",
  20480:"TV Power On",
  20481:"TV Power Off",
  62:"Mute",
  65:"Volume Down",
  66:"Volume Up",
  24576:"Sys Info",
  24577:"Mode",
  24578:"Loc Remote",
  24579:"Absolute Pointing Packet",
  24580:"Relative Pointing Packet",
  24581:"Relative Horizontal Scroll",
  24582:"Relative Vertical Scroll",
  24583:"Absolute Horizontal Scroll",
  24584:"Absolute Vertical Scroll",
  26625:"Sling Cursor On",
  26626:"Sling Cursor Off",
  26627:"Sling Hover On",
  26628:"Sling Hover Off",
  26629:"Sling Set X/Y",
  26881:"Focus",
  26882:"Enable",
  26883:"Reshape",
  26884:"Mouse Scroll Up",
  26885:"Mouse Scroll Down",
  26886:"Mouse Scroll Right",
  26887:"Mouse Scroll Left",
  26888:"Scroll Up",
  26889:"Scroll Down",
  26890:"Scroll Right",
  26891:"Scroll Left",
  26892:"Scroll No Reshape",
  26893:"Toggle",
  26894:"Quit App",
  26895:"Set TV1 to Browser Scroll Mode",
  26896:"Set TV2 to Browser Scroll Mode",
  26897:"Cursor Draw State",
  26898:"Cursor Positional Change",
  26899:"Inhibit Key",
  26900:"Uninhibit Key",
  26901:"Virtual Keyboard Hide",
  26902:"Virtual Keyboard Show",
  26903:"Virtual Keyboard Auto Display Enable",
  26904:"Virtual Keyboard Auto Display Disable",
  26905:"Ui Action Request Confirm",
  26906:"Ui Action Request Cancel",
  26907:"Ui Action Request Other",
  26908:"Color 1",
  26909:"Color 2",
  26910:"Color 3",
  26911:"Color 4",
  32784:"q",
  32785:"w",
  32786:"e",
  32787:"r",
  32788:"t",
  32789:"y",
  32790:"u",
  32791:"i",
  32792:"o",
  32793:"p",
  32798:"a",
  32799:"s",
  32800:"d",
  32801:"f",
  32802:"g",
  32803:"h",
  32804:"j",
  32805:"k",
  32806:"l",
  32812:"z",
  32813:"x",
  32814:"c",
  32815:"v",
  32816:"b",
  32817:"n",
  32818:"m",
  32827:"F1",
  32828:"F2",
  32829:"F3",
  32830:"F4",
  32831:"F5",
  32832:"F6",
  32833:"F7",
  32834:"F8",
  32835:"F9",
  32836:"F10",
  32855:"F11",
  32856:"F12",
  32780:"-",
  32781:"=",
  32808:"Apostrophe",
  32819:"Comma",
  32820:".",
  32821:"/",
  32811:"Backslash",
  32825:"Space",
  32809:"`",
  32794:"Left Brace",
  32795:"Right Brace",
  32807:";",
  32782:"Backspace",
  32879:"Delete",
  32870:"Home",
  32875:"End",
  32783:"Tab",
  32826:"Capslock",
  32810:"Left Shift",
  32822:"Right Shift",
  33040:"Mouse Left",
  33042:"Mouse Center",
  33041:"Mouse Right",
  36880:"Q",
  36881:"W",
  36882:"E",
  36883:"R",
  36884:"T",
  36885:"Y",
  36886:"U",
  36887:"I",
  36888:"O",
  36889:"P",
  36894:"A",
  36895:"S",
  36896:"D",
  36897:"F",
  36898:"G",
  36899:"H",
  36900:"J",
  36901:"K",
  36902:"L",
  36908:"Z",
  36909:"X",
  36910:"C",
  36911:"V",
  36912:"B",
  36913:"N",
  36914:"M",
  36905:"~",
  36866:"!",
  36867:"@",
  36869:"$",
  36870:"%",
  36871:"^",
  36872:"&",
  36874:"Left Paren",
  36875:"Right Paren",
  36876:"_",
  36877:"+",
  36890:"{",
  36891:"}",
  36907:"|",
  36903:":",
  36904:"Quote",
  36915:"<",
  36916:">",
  36917:"?",
  39312:"Sync"
}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python translate_script.py <input_file>")
    else:
        translate_file(sys.argv[1])
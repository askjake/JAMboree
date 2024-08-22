
		 document.addEventListener("DOMContentLoaded", function () {
            fetch('/hostname')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('host-name').textContent = data.hostname;
                })
                .catch(error => console.error('Error fetching hostname:', error));
        });
		
function fetchAppsList() {
    fetch('/api/apps')
        .then(response => response.json())
        .then(data => {
            console.log("Fetched apps:", data);  // Check that data is correctly fetched
            populateAppList(data);
			fetchStbAppList();
        })
        .catch(error => {
            console.error('Error fetching apps:', error);
            printToOutput(`Error fetching apps: ${error}`);
        });
}

function populateAppList(apps) {
    const appListDiv = document.getElementById('app-list');
    appListDiv.innerHTML = '';  // Clear the current options if any

    apps.forEach(app => {
        const opt = document.createElement('option');
        opt.value = app.filename;
        opt.text = `${app.date} - ${app.filename}`;
        console.log(`Appending option: ${opt.text}`);  // Log each appended option
        appListDiv.appendChild(opt);
    });

    console.log(appListDiv.innerHTML);  // Log the final HTML of the select element
    printToOutput("App list populated.");
}

function loadApps() {
    const selectedApp = document.querySelector('#app-list option:checked');
    const stbListElement = document.querySelector('#stb-list'); // Ensure this ID matches your actual HTML ID

    console.log('Selected app:', selectedApp); // Debugging: Log selected app
    console.log('Selected STB list element:', stbListElement); // Debugging: Log the STB list element

    if (!selectedApp) {
        console.error('Please select an app.');
        printToOutput('Please select an app.');
        return;
    }

    if (!stbListElement) {
        console.error('STB list element not found.');
        printToOutput('STB list element not found.');
        return;
    }

    const selectedStbs = Array.from(stbListElement.selectedOptions).map(opt => opt.value);

    console.log('Selected STBs:', selectedStbs); // Debugging: Log selected STB values

    if (selectedStbs.length === 0) {
        console.error('Please select one or more STBs.');
        printToOutput('Please select one or more STBs.');
        return;
    }

    const appFilename = selectedApp.value;
    console.log('Selected app filename:', appFilename); // Debugging: Log the selected app filename

    selectedStbs.forEach(stb => {
        const data = {
            app: appFilename,
            stb: stb,
        };

        console.log('Data to send:', data); // Debugging: Log data that will be sent to the server

        fetch('/api/load_app', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
            .then(response => response.json())
            .then(result => {
                if (result.status) {
                    console.log(`App ${appFilename} successfully loaded onto STB ${stb}.`);
                    printToOutput(`App ${appFilename} successfully loaded onto STB ${stb}.`);
                } else {
                    console.error(`Failed to load app: ${result.error}`);
                    printToOutput(`Failed to load app: ${result.error}`);
                }
            })
            .catch(error => {
                console.error('Error loading app:', error);
                printToOutput(`Error loading app: ${error}`);
            });
    });
}

function printToOutput(message) {
    const outputDiv = document.getElementById('output');
    const newMessage = document.createElement('p');
    newMessage.textContent = message;
    outputDiv.appendChild(newMessage);
}

// Call fetchAppsList when the page loads
window.onload = function() {
    const activeKeys = new Map(); // Track which keys are currently pressed

    // Bind events to all buttons in the remote container
    document.querySelectorAll('.button').forEach(button => {
        button.addEventListener('mousedown', function() {
            this.startTime = Date.now(); // Record start time
            playClickSound(); // Play sound on mousedown
            this.classList.add('pressed'); // Add pressed effect
        });

        button.addEventListener('mouseup', function() {
            const pressDuration = Date.now() - this.startTime; // Calculate press duration
            console.log(`Button ${this.id} was pressed for ${pressDuration} milliseconds.`);
            sendCommandToStbs(this.id, pressDuration); // Send command with calculated delay
            this.classList.remove('pressed'); // Remove pressed effect
        });
    });

    // Key mapping for the remote buttons
    const keyMapping = {
        'Digit1': 'one',
        'Digit2': 'two',
        'Digit3': 'three',
        'Digit4': 'four',
        'Digit5': 'five',
        'Digit6': 'six',
        'Digit7': 'seven',
        'Digit8': 'eight',
        'Digit9': 'nine',
        'Digit0': 'zero',
        'ArrowUp': 'up',
        'ArrowDown': 'down',
        'ArrowLeft': 'left',
        'ArrowRight': 'right',
        'Enter': 'enter',
        'Escape': 'back',
        'KeyD': 'dvr',
        'KeyH': 'home',
        'KeyG': 'guide',
        'KeyO': 'options',
        'KeyM': 'menu',
        'KeyI': 'info',
    };

    // Add keydown event listener
    document.addEventListener('keydown', function(event) {
        const buttonId = keyMapping[event.code];
        if (buttonId && !activeKeys.has(event.code)) {
            activeKeys.set(event.code, Date.now()); // Start time for the key
            console.log(`Keydown detected: ${event.code}, triggering button with ID: ${buttonId}`);
            const button = document.getElementById(buttonId);
            if (button) {
                button.classList.add('pressed'); // Visually show the button as pressed
                button.click(); // Trigger the button click
            }
        }
    });

    // Add keyup event listener to remove 'pressed' class after key is released
    document.addEventListener('keyup', function(event) {
        const buttonId = keyMapping[event.code];
        if (buttonId && activeKeys.has(event.code)) {
            const startTime = activeKeys.get(event.code);
            const pressDuration = Date.now() - startTime; // Calculate press duration
            console.log(`Keyup detected: ${event.code}, releasing button with ID: ${buttonId}, press duration: ${pressDuration}ms`);

            const button = document.getElementById(buttonId);
            if (button) {
                sendCommandToStbs(buttonId, pressDuration); // Send command
                button.classList.remove('pressed'); // Remove pressed effect
            }
            activeKeys.delete(event.code); // Remove the key from the activeKeys map
        }
    });
};

// Play click sound function
function playClickSound() {
    const clickSound = document.getElementById('click-sound');
    if (clickSound) {
        clickSound.currentTime = 0; // Reset sound to start
        clickSound.play().catch(error => console.log('Audio playback error:', error)); // Handle potential playback errors
    }
}

// Fetch STB list and populate a multi-selection list
function fetchStbList() {
    fetch('/get-stb-list')
        .then(response => response.json())
        .then(data => {
            populateStbList(data.stbs);
        })
        .catch(error => {
            console.error('Error fetching STBs:', error);
            printToOutput(`Error fetching STBs: ${error}`);
        });
}

// Fetch STB list and populate a multi-selection list
function fetchStbAppList() {
    fetch('/get-stb-list')
        .then(response => response.json())
        .then(data => {
            populateStbAppList(data.stbs);
        })
        .catch(error => {
            console.error('Error fetching STBs:', error);
            printToOutput(`Error fetching STBs: ${error}`);
        });
}
 
function populateStbAppList(stbs) {
    const stbListDiv = document.getElementById('stb-list');
    stbListDiv.innerHTML = ''; // Clear previous content

    // Iterate over the STBs and append options
    Object.entries(stbs).forEach(([stbName, stbDetails]) => {
        const opt = document.createElement('option');
        opt.value = stbName;
        opt.text = stbName;
        stbListDiv.appendChild(opt);

        // Debugging log
        console.log(`Appending STB option: ${stbName}`);
        //printToOutput(`Appending STB option: ${stbName}`);
    });

    console.log(stbListDiv.innerHTML); // Log the final HTML of the select element
}

function populateStbList(stbs) {
    console.log("Populating STB List with data:", stbs);  // Log the input data
    printToOutput("Populating STB List with data...");  // Print to output div
    const stbListDiv = document.getElementById('stb-list');
    if (!stbListDiv) {
        console.error("Error: 'stb-list' element not found.");
        //printToOutput("Error: 'stb-list' element not found.");
        return;
    }

    stbListDiv.innerHTML = ''; // Clear previous content
    stbListDiv.classList.add('grid-container'); // Add grid container class for styling

    const listBox = document.createElement('select');
    listBox.id = 'stbList';
    listBox.multiple = true;
    listBox.style.width = '100%';

    const numberOfStbs = Object.keys(stbs).length;
    const itemHeight = 20;
    const maxHeight = window.innerHeight * 0.8;

    const listBoxHeight = Math.min(numberOfStbs * itemHeight, maxHeight);
    listBox.style.height = `${listBoxHeight}px`;

    Object.entries(stbs).forEach(([stbName, stbDetails]) => {
        const opt = document.createElement('option');
        opt.value = stbName;
        opt.text = `${stbName}`;
        opt.setAttribute('data-remote', stbDetails.remote);
        listBox.appendChild(opt);
        console.log(`Appending STB option: ${opt.text}`);  // Log each appended option
        //printToOutput(`Appending STB option: ${opt.text}`);
    });

    stbListDiv.appendChild(listBox);

    const selectedStbs = getCookie('selectedStbs');
    if (selectedStbs) {
        const selectedValues = selectedStbs.split(',');
        for (const option of listBox.options) {
            if (selectedValues.includes(option.value)) {
                option.selected = true;
            }
        }
    }

    listBox.onchange = function() {
        const selectedOptions = Array.from(this.selectedOptions).map(option => option.value);
        setCookie('selectedStbs', selectedOptions.join(','), 365);
    };

    listBox.scrollTop = 0;
}

// Function to send commands to all selected STBs
function sendCommandToStbs(buttonId, delay) {
    const hostname = window.location.hostname;
    const listBox = document.getElementById('stbList');
    const selectedStbs = Array.from(listBox.selectedOptions).map(option => option.value);

    selectedStbs.forEach(stbName => {
        // Find the selected option element by value (stbName)
        const selectedOption = Array.from(listBox.options).find(option => option.value === stbName);

        if (selectedOption) {
            const remote = selectedOption.getAttribute('data-remote');
            const delayInt = parseInt(delay, 10);
            const url = `http://${hostname}:5001/auto/${remote}/${stbName}/${buttonId}/${delayInt}/`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    console.log('Command response:', data);
                    printToOutput(`Command response: ${JSON.stringify(data)}`);
                });
        } else {
            console.error(`STB option for ${stbName} not found.`);
            //printToOutput(`STB option for ${stbName} not found.`);
        }
    });
}

// Utility function to set a cookie
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + d.toUTCString();
    document.cookie = name + "=" + value + ";" + expires + ";path=/";
}

// Utility function to get a cookie by name
function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; ca.length > i; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Initialize fetching on page load
window.onload = function() {
    fetchAppsList();
    fetchStbList();
};

window.onload = function() {
	    console.log('Script loaded and window.onload triggered');

    const activeKeys = new Map(); // Track which keys are currently pressed

    // Bind events to all buttons in the remote container
    const buttons = document.querySelectorAll('.button');
    if (buttons.length === 0) {
        console.error("No buttons found with the class '.button'");
    }

    buttons.forEach(button => {
        console.log(`Attaching events to button with ID: ${button.id}`);
        
        button.addEventListener('mousedown', function() {
            this.startTime = Date.now(); // Record start time
            this.classList.add('pressed'); // Add pressed effect
            console.log(`Button ${this.id} mousedown event triggered`);
        });

        button.addEventListener('mouseup', function() {
            const pressDuration = Date.now() - this.startTime; // Calculate press duration
            console.log(`Button ${this.id} was pressed for ${pressDuration} milliseconds.`);
            sendCommandToStbs(this.id, pressDuration); // Send command with calculated delay
            this.classList.remove('pressed'); // Remove pressed effect
            console.log(`Button ${this.id} mouseup event triggered`);
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
        .catch(error => console.error('Error fetching STBs:', error));
}

 
function populateStbList(stbs) {
    console.log("Populating STB List with data:", stbs);  // Log the input data
    const stbListDiv = document.getElementById('stb-list');
    if (!stbListDiv) {
        console.error("Error: 'stb-list' element not found.");
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
        const selectedOption = Array.from(listBox.options).find(option => option.value === stbName);

        if (selectedOption) {
            const remote = selectedOption.getAttribute('data-remote');
            const delayInt = parseInt(delay, 10);
            const url = `http://${hostname}:5001/auto/${remote}/${stbName}/${buttonId}/${delayInt}`;
            fetch(url)
                .then(response => response.json())
                .then(data => console.log('Command response:', data))
                .catch(error => console.error('Error sending command:', error));
        } else {
            console.error(`STB option for ${stbName} not found.`);
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

    fetchStbList();
};

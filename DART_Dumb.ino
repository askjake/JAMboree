#include <Wire.h>

// Corrected definition using 'constexpr' with type specifier
constexpr byte I2C_SLAVE_ADDR = 0x34; // I2C address in hexadecimal
constexpr int RESET_PIN = A7;   // Pin used to reset the remotes
volatile bool ackReceived = false; // Flag to indicate acknowledgment received
unsigned long ackTimeout = 100; // Timeout for waiting for acknowledgment (in ms)

// Define registers or constants as needed
byte CFG_REG = 0xAF;
byte INT_REG = 0x01;
byte EVT_REG = 0x01;
byte BLANK = 0x00;

const int remotePins[16] = {12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 13, A0, A1, A2, A3};

volatile byte readMode = 0; 
volatile int receivedValue = 0;
boolean clearInterruptFlag = false;
boolean debug = false;          // Debug mode flag
boolean initFlag = true;        // Flag to initialize CFG_REG on powerup/reset
volatile byte KEY_CMD = 0;      // Variable to store the KEY_CMD received from Serial

// Define button#action mapping
const char* buttonActions[40][2] = {
    {"81", "01"}, {"8C", "0C"}, {"8B", "0B"}, {"83", "03"}, {"95", "15"}, {"96", "16"}, 
    {"97", "17"}, {"98", "18"}, {"99", "19"}, {"9A", "1A"}, {"A2", "22"}, {"A3", "23"}, 
    {"A4", "24"}, {"9F", "1F"}, {"A0", "20"}, {"A1", "21"}, {"A9", "29"}, {"AA", "2A"}, 
    {"AB", "2B"}, {"AC", "2C"}, {"AD", "2D"}, {"AE", "2E"}, {"B6", "36"}, {"B7", "37"}, 
    {"B8", "38"}, {"B3", "33"}, {"B4", "34"}, {"B5", "35"}, {"BD", "3D"}, {"BE", "3E"}, 
    {"BF", "3F"}, {"C0", "40"}, {"C1", "41"}, {"C2", "42"}, {"EF", "6F"}, {"F0", "70"}, 
    {"F1", "71"}, {"F2", "72"}, {"8C", "8B"}, {"0B", "03"}
};

void setup() {
  Serial.begin(115200); // Start serial communication at 115200 baud rate
  Wire.begin(I2C_SLAVE_ADDR); // Initialize the I2C bus as a slave
  Wire.onRequest(requestEvent); // Register requestEvent() to handle I2C requests
  Wire.onReceive(receiveEvent); // Register to handle I2C receive events

  // Initialize interrupt pins as outputs and set them HIGH
  for (int i = 0; i < 16; i++) {
    pinMode(remotePins[i], OUTPUT); // Set each remote pin as output
    digitalWrite(remotePins[i], HIGH); // Set each pin HIGH initially
  }
  
  pinMode(RESET_PIN, OUTPUT);  // Set the RESET_PIN as output
  digitalWrite(RESET_PIN, HIGH); // Set RESET_PIN HIGH initially

  Serial.println("11.05.2024 Jake Montgomery (That Was Good)"); // Print identification message
  Serial.flush(); 
}

void loop() {
  static String inputString = ""; // A String to hold incoming data
  static boolean inputComplete = false; // Whether the input string is complete

  // Check if there is data available in the serial buffer
  if (Serial.available()) {
    char inChar = (char)Serial.read(); // Read the incoming character
    if (inChar == '\n') { // Check if the character is newline
      inputComplete = true; // Set the inputComplete flag to true
      parseInput(inputString);
      inputString = ""; // Clear the input string
      inputComplete = false; // Reset the inputComplete flag
    } else {
      inputString += inChar; // Append character to input string
    }
  }
}

void parseInput(String input) {
  input.trim(); // Remove leading/trailing whitespace
  Serial.println("Received input: " + input); // Debug print

  // Check for 'reset' command
  if (input == "reset") {
    resetRemotes();
    return;
  }

  int remoteNum, buttonNum, delayMs; 
  char action[10];  // To hold the action string (up/down)
  byte keyCmdDown, keyCmdUp;

  // Check if the input matches the first format: remoteNum, keyCmdDown, keyCmdUp, delayMs
  if (sscanf(input.c_str(), "%d %hhx %hhx %d", &remoteNum, &keyCmdDown, &keyCmdUp, &delayMs) == 4) {
    int interruptPin = convertNumToPin(remoteNum); // Convert remote number to pin number
    if (interruptPin >= 0) {
      // Send KEY_CMD_DOWN and wait for acknowledgment
      if (!sendKeyCmdAndWaitForAck(interruptPin, keyCmdDown, ackTimeout)) {
        releaseAllButtons(remoteNum);
        return;
      }

      delay(delayMs); // Wait for the specified delay

      // Send KEY_CMD_UP and wait for acknowledgment
      if (!sendKeyCmdAndWaitForAck(interruptPin, keyCmdUp, ackTimeout)) {
        releaseAllButtons(remoteNum);
        return;
      }

      // Send KEY_CMD_UP again for reliability
      if (!sendKeyCmdAndWaitForAck(interruptPin, keyCmdUp, ackTimeout)) {
        releaseAllButtons(remoteNum);
        return;
      }

      Serial.print(remoteNum); // Print the remote number
      Serial.print(keyCmdDown); 
      Serial.println(keyCmdUp); 
      Serial.flush(); 
      delay(2);
    }
  }
  // Check if the input matches the second format: remoteNum, buttonNum, action
  else if (sscanf(input.c_str(), "%d %d %s", &remoteNum, &buttonNum, action) == 3) {
    if (buttonNum == 86) {
      releaseAllButtons(remoteNum);
    } else if (buttonNum == 99) {
      resetRemotes();
    } else {
      if (strcmp(action, "down") == 0) {
        KEY_CMD = strtol(buttonActions[buttonNum - 1][0], NULL, 16);
      } else if (strcmp(action, "up") == 0) {
        KEY_CMD = strtol(buttonActions[buttonNum - 1][1], NULL, 16);
      } else {
        Serial.println("Invalid action!"); // Debug print
        Serial.flush();
        return;
      }

      int interruptPin = convertNumToPin(remoteNum); // Convert remote number to pin number
      if (interruptPin >= 0 && buttonNum > 0 && buttonNum <= 40) {
        // Send KEY_CMD and wait for acknowledgment
        if (!sendKeyCmdAndWaitForAck(interruptPin, KEY_CMD, ackTimeout)) {
          releaseAllButtons(remoteNum);
          return;
        }
      } else {
        Serial.println("Invalid remote number or button number " + String(remoteNum)); // Debug print
        Serial.flush();
      }
    }
  } else {
    Serial.print("Failed to parse input! "); // Debug print
    Serial.println(input);
    Serial.flush();
  }
}

// Function to send key command and wait for acknowledgment
bool sendKeyCmdAndWaitForAck(int interruptPin, byte keyCmd, unsigned long timeout) {
  ackReceived = false; // Reset ackReceived flag
  triggerKeyCmd(interruptPin, keyCmd);

  // Wait for acknowledgment after triggering the key command
  unsigned long startTime = millis();
  while (!ackReceived) {
    if (millis() - startTime > timeout) {
      Serial.println("Timeout waiting for acknowledgment");
      Serial.flush();
      return false;
    }
  }
  return true;
}

void releaseAllButtons(int remoteNum) {
  for (int i = 1; i <= 1; i++) {
    KEY_CMD = strtol(buttonActions[i - 1][1], NULL, 16); // "up" action for each button
    int pin = convertNumToPin(remoteNum);
    if (pin >= 0) {
      // Send KEY_CMD and wait for acknowledgment
      if (!sendKeyCmdAndWaitForAck(pin, KEY_CMD, ackTimeout)) {
        break; // Timeout: proceed even if acknowledgment wasn't received
      }
    }
  }
}

// I2C request event handler
void requestEvent() {
  if (clearInterruptFlag) {
    Wire.write(BLANK); // Write BLANK to clear interrupt
    clearInterruptFlag = false; // Reset the flag after clearing the interrupt
  } else {
    //Wire.write(CFG_REG); 
    Wire.write(0xAF);
  }
  Wire.write(INT_REG); // Write interrupt register
  Wire.write(EVT_REG); // Write event register
  Wire.write(KEY_CMD); // Write key command
  for (int i = 0; i < 11; i++) {
    Wire.write(BLANK); // Write blank bytes to fill the response
  }
}

// Convert remote number to corresponding pin number
int convertNumToPin(int remoteNum) {
    if (remoteNum >= 1 && remoteNum <= 16) {
      return remotePins[remoteNum - 1];
    }
    return -1; // Return -1 for invalid pin numbers
}

// Reset all remotes by toggling the RESET_PIN
void resetRemotes() {
  digitalWrite(RESET_PIN, LOW); // Set RESET_PIN LOW to trigger reset
  delay(500);  // Wait for 250 milliseconds
  digitalWrite(RESET_PIN, HIGH);  // Set RESET_PIN HIGH again
}

// Trigger a key command by toggling the specified pin
void triggerKeyCmd(int pin, byte keyCmd) {
  KEY_CMD = keyCmd; // Set the key command to the specified value
  digitalWrite(pin, LOW); // Set the pin LOW to trigger the command
  delay(2); // Delay for a short duration to simulate key press
  digitalWrite(pin, HIGH); // Set the pin HIGH again
}

// I2C receive event handler
void receiveEvent(int howMany) {
  byte byteCount = 0;
  byte byteCursor = 0;
  byte receivedValues[45]; // Array to store received values
  byte receivedByte = 0;
  byte command = 0;
  byte byteRead = 0;
  receivedValue = 0;
  
  // Read all available bytes from the I2C buffer
  while (Wire.available()) {
    byteRead = Wire.read(); // Read a byte from the buffer
    if (byteCount == 0) {
      readMode = byteRead; // Set readMode to the first byte
      command = byteRead; // Set command to the first byte
    } else {
      receivedByte = byteRead; // Store received byte
      receivedValues[byteCursor] = receivedByte; // Store in the array
      byteCursor++;
    }
    byteCount++;
  }

  // Convert received values into an integer value
  for (byte otherByteCursor = byteCursor; otherByteCursor > 0; otherByteCursor--) {
    receivedValue += (unsigned long)receivedValues[otherByteCursor - 1] << ((byteCursor - otherByteCursor) * 8);
  }

  // Handle different commands based on received data
  if (initFlag) { 
    if (command == 1) { // Allows setting of initFlag once during remote boot  
      CFG_REG = receivedByte; // Set CFG_REG to received value
      initFlag = false; // Clear initFlag
    }
    return;
  } 
  if (command == 2) { 
    clearInterruptFlag = true; // Set clearInterruptFlag to clear interrupts
    ackReceived = true; // Acknowledgment received only after full sequence is complete
    return;
  } else { 
    return;
  }
}

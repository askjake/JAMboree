#!/bin/bash

# Function to compare version numbers
version_gt() {
    [ "$1" = "$2" ] && return 1 || [ "$1" = "$(echo -e "$1\n$2" | sort -V | head -n1)" ] && return 1 || return 0
}

# Function to install Python 3.11 if it's not present
install_python_311() {
    echo "Python 3.11 or higher is required. Installing Python 3.11..."

    # Update package list and install required packages
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y wget build-essential libssl-dev zlib1g-dev libncurses5-dev \
        libgdbm-dev libnss3-dev libreadline-dev libffi-dev curl libbz2-dev libsqlite3-dev

    # Download and install Python 3.11 from source
    cd /usr/src
    sudo wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz
    sudo tar xzf Python-3.11.0.tgz
    cd Python-3.11.0
    sudo ./configure --enable-optimizations
    sudo make altinstall

    # Verify the installation
    if ! command -v python3.11 &>/dev/null; then
        echo "Failed to install Python 3.11. Exiting."
        exit 1
    fi

    # Clean up
    cd ..
    sudo rm -rf Python-3.11.0 Python-3.11.0.tgz
}

# Check if Python 3.11 or higher is installed
if command -v python3.11 &>/dev/null; then
    PYTHON_VERSION=$(python3.11 --version | awk '{print $2}')
else
    PYTHON_VERSION="0"
fi

REQUIRED_VERSION="3.11.0"

if version_gt "$REQUIRED_VERSION" "$PYTHON_VERSION"; then
    install_python_311
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d "vJAM" ]; then
    python3.11 -m venv vJAM
fi

if [ ! -d "vJAM" ]; then
    echo "Failed to create virtual environment. Exiting."
    exit 1
fi

source vJAM/bin/activate

# Upgrade pip and install required packages
pip install --upgrade pip

# Install additional packages
pip install cmake pyarrow

# Install packages from requirements.txt
pip install -r requirements.txt --break-system-packages

# Add ~/JAMboree to PATH if not already present
if ! grep -q "~/JAMboree" /etc/profile; then
    echo 'export PATH="$PATH:~/JAMboree"' | sudo tee -a /etc/profile
    source /etc/profile
fi

# Create a symlink for BOOM.sh if it doesn't exist
if [ ! -f /usr/local/bin/boom ]; then
    sudo ln -s ~/JAMboree/BOOM.sh /usr/local/bin/boom
fi

# Run the Python scripts
python scripts/stb_search.py &
python JAMboree.py

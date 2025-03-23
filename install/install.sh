#!/bin/bash

# Nuki Smart Lock Notification System Installation Script
# This script installs the Nuki Smart Lock Notification System on a Raspberry Pi

echo "====================================================="
echo "  Nuki Smart Lock Notification System Installation"
echo "====================================================="

# Functions
check_command() {
    command -v $1 >/dev/null 2>&1 || { 
        echo >&2 "Error: Required command '$1' not found."; 
        echo "Please install it first and run this script again."; 
        exit 1; 
    }
}

# Check requirements
check_command python3
check_command pip3
check_command systemctl

# Configuration
INSTALL_DIR="/root/nukiweb"
CONFIG_DIR="$INSTALL_DIR/config"
LOGS_DIR="$INSTALL_DIR/logs"
SCRIPTS_DIR="$INSTALL_DIR/scripts"
WEB_DIR="$INSTALL_DIR/web"
SECURITY_DIR="$INSTALL_DIR/security"

echo "Installation directory: $INSTALL_DIR"

# Create directories
echo -e "\n[1/7] Creating directories..."
sudo mkdir -p $INSTALL_DIR
sudo mkdir -p $CONFIG_DIR
sudo mkdir -p $LOGS_DIR
sudo mkdir -p $SCRIPTS_DIR
sudo mkdir -p $SCRIPTS_DIR/nuki
sudo mkdir -p $WEB_DIR
sudo mkdir -p $SECURITY_DIR

# Copy files
echo -e "\n[2/7] Copying files..."
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Copy scripts
sudo cp -r $script_dir/scripts/* $SCRIPTS_DIR/
sudo cp -r $script_dir/scripts/nuki/* $SCRIPTS_DIR/nuki/

# Copy web interface
sudo cp -r $script_dir/web/* $WEB_DIR/

# Copy security module
sudo cp -r $script_dir/security/* $SECURITY_DIR/

# Copy config examples
sudo cp $script_dir/config/config.ini.example $CONFIG_DIR/config.ini.example
sudo cp $script_dir/config/credentials.ini.example $CONFIG_DIR/credentials.ini.example

# Create Python virtual environment
echo -e "\n[3/7] Setting up Python virtual environment..."
cd $INSTALL_DIR
sudo python3 -m venv venv
sudo $INSTALL_DIR/venv/bin/pip install --upgrade pip
sudo $INSTALL_DIR/venv/bin/pip install -r $script_dir/requirements.txt
sudo $INSTALL_DIR/venv/bin/pip install -r $script_dir/requirements-web.txt

# Set file permissions
echo -e "\n[4/7] Setting file permissions..."
sudo chmod +x $SCRIPTS_DIR/nuki_monitor.py
sudo chmod +x $WEB_DIR/app.py
sudo chmod +x $SCRIPTS_DIR/configure.py
sudo chmod +x $SCRIPTS_DIR/get_telegram_chat_id.py

# Create example configuration if it doesn't exist
echo -e "\n[5/7] Creating example configuration files..."
if [ ! -f "$CONFIG_DIR/config.ini" ]; then
    sudo cp $CONFIG_DIR/config.ini.example $CONFIG_DIR/config.ini
    echo "Created example config.ini - please edit this file with your settings"
fi

if [ ! -f "$CONFIG_DIR/credentials.ini" ]; then
    sudo cp $CONFIG_DIR/credentials.ini.example $CONFIG_DIR/credentials.ini
    echo "Created example credentials.ini - please edit this file with your API tokens"
    sudo chmod 600 $CONFIG_DIR/credentials.ini
fi

# Install systemd services
echo -e "\n[6/7] Installing systemd services..."
sudo cp $script_dir/install/nuki-monitor.service /etc/systemd/system/
sudo cp $script_dir/install/nuki-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nuki-monitor.service
sudo systemctl enable nuki-web.service

# Configuration
echo -e "\n[7/7] Running initial configuration..."
cd $SCRIPTS_DIR
sudo $INSTALL_DIR/venv/bin/python configure.py --initial-setup

# Completion
echo -e "\n====================================================="
echo "Installation complete!"
echo "====================================================="
echo ""
echo "To start the services:"
echo "  sudo systemctl start nuki-monitor.service"
echo "  sudo systemctl start nuki-web.service"
echo ""
echo "To configure the system:"
echo "  cd $SCRIPTS_DIR"
echo "  sudo $INSTALL_DIR/venv/bin/python configure.py"
echo ""
echo "Web interface will be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Don't forget to edit your configuration files at:"
echo "  $CONFIG_DIR/config.ini"
echo "  $CONFIG_DIR/credentials.ini"
echo ""
echo "For more information, visit:"
echo "  https://github.com/your-username/nuki-smart-lock-notification"
echo "====================================================="

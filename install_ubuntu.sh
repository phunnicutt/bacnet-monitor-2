#!/bin/bash
#############################################################################
# install_ubuntu.sh - BACmon Installation Script for Ubuntu
#############################################################################
# 
# This script installs and configures BACmon (BACnet Monitor) on Ubuntu systems.
# It has been updated for Python 3 compatibility and modern Ubuntu versions 
# (20.04, 22.04+).
#
# USAGE:
#   ./install_ubuntu.sh
#
# REQUIREMENTS:
#   - Ubuntu 18.04 or higher (20.04 or 22.04 recommended)
#   - Internet access for package installation
#   - Root privileges (for apt and service management)
#
# NOTES:
#   - This script will install and configure all required dependencies
#   - Python 3 is required and will be installed if not present
#   - The script creates a system user 'bacmon' to run services
#   - Services installed: Apache2, Redis, BACmon, BACmonLogger
#
# AUTHOR:
#   Original script by BACmon developers
#   Updated for Python 3 compatibility (2023)
#
#############################################################################

# Exit on error
set -e

# Print script banner
cat << "EOF"
______          _____                        
| ___ \        /  __ \                       
| |_/ /_ _  ___| /  \/_ __ ___   ___  _ __  
| ___ \ | |/ __| |   | '_ ' _ \ / _ \| '_ \ 
| |_/ / |_| (__| \__/\ | | | | | (_) | | | |
\____/ \__,\___|____/_| |_| |_|\___/|_| |_|
                                           
BACmon Installation Script for Ubuntu
------------------------------------
EOF

# Print diagnostic information
echo "System Information:"
echo "- $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)"
echo "- Kernel: $(uname -r)"
echo "- Date: $(date)"
echo

# location of the INI file
BACMON_HOME=/home/bacmon
BACMON_INI=$BACMON_HOME/BACmon.ini

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to handle errors
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Function to check Ubuntu version
check_ubuntu_version() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ -n "$VERSION_ID" ]; then
            echo "Detected Ubuntu version: $VERSION_ID"
            UBUNTU_VERSION=$VERSION_ID
            # Check if version is supported
            if (( $(echo "$UBUNTU_VERSION < 18.04" | bc -l) )); then
                echo "WARNING: This script is optimized for Ubuntu 18.04 or higher."
                echo "You are running Ubuntu $UBUNTU_VERSION which may not be fully supported."
                read -p "Continue anyway? [y/n] " continue_anyway
                if [ "$continue_anyway" != "y" ]; then
                    echo "Installation aborted."
                    exit 1
                fi
            fi
            return 0
        fi
    fi
    echo "Warning: Could not determine Ubuntu version"
    return 1
}

# Check Ubuntu version
check_ubuntu_version

# Function to check if systemd is available
has_systemd() {
    [ -d "/etc/systemd/system" ]
}

# Function to check Python 3 installation
check_python3() {
    echo "Checking Python 3 installation..."
    if command_exists python3; then
        python3_version=$(python3 --version)
        echo "✓ $python3_version is installed"
        return 0
    else
        echo "✗ Python 3 is not installed"
        return 1
    fi
}

# Function to install Python 3 if not present
install_python3() {
    echo "Installing Python 3..."
    sudo apt update || handle_error "Failed to update package list"
    sudo apt install -y python3 python3-dev || handle_error "Failed to install Python 3"
    
    if ! check_python3; then
        handle_error "Failed to install Python 3. Please install it manually and try again."
    fi
}

# Function to check if pip3 is installed
check_pip3() {
    echo "Checking pip3 installation..."
    if command_exists pip3; then
        pip3_version=$(pip3 --version)
        echo "✓ $pip3_version is installed"
        return 0
    else
        echo "✗ pip3 is not installed"
        return 1
    fi
}

# Function to install pip3 if not present
install_pip3() {
    echo "Installing pip3..."
    sudo apt update || handle_error "Failed to update package list"
    sudo apt install -y python3-pip || handle_error "Failed to install pip3"
    
    if ! check_pip3; then
        handle_error "Failed to install pip3. Please install it manually and try again."
    fi
}

# Verify Python 3 installation at the beginning
echo "Verifying Python 3 installation..."
if ! check_python3; then
    echo "Python 3 is required for BACmon."
    read -p "Install Python 3 now? [y/n] " install_python
    if [ "$install_python" = "y" ]; then
        install_python3
    else
        handle_error "Python 3 is required to proceed. Exiting."
    fi
fi

# Verify pip3 installation after Python 3 check
echo "Verifying pip3 installation..."
if ! check_pip3; then
    echo "pip3 is required for BACmon."
    read -p "Install pip3 now? [y/n] " install_pip
    if [ "$install_pip" = "y" ]; then
        install_pip3
    else
        handle_error "pip3 is required to proceed. Exiting."
    fi
fi

cat << EOF

========== Create a BACmon User

The BACmon configuration and log files are owned by a 'bacmon' system user.  The
daemon process that analyzes the incoming packets and the cron script used
to keep the capture log directory from filling up also run as this user.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo adduser --system bacmon

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi
if [ ! -d "$BACMON_HOME" ] ;
then
    echo "Home directory missing."
    exit 1
fi

cat << EOF

========== Network Time Protocol

It is important to keep the server's clock synchronized closely with internet 
time servers, particularly when there are more than one instance of BACmon 
running on an intranet and users are attempting to analyze events that span
networks.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y ntp ntpdate

    sudo systemctl stop ntp

    echo
    echo At the next prompt you can provide the DNS name of a local NTP
    echo server or leave it blank to default to ntp.ubuntu.com.
    echo
    read -p "NTP server? " ntpserver || exit 1
    if [ "$ntpserver" != "" ] ;
    then
        # create a temp file
        TMPFILE=`mktemp` || exit 1
        sed "s/ntp.ubuntu.com/$ntpserver/g" < /etc/ntp.conf > $TMPFILE
        
        # check for differences, maybe nothing changed
        diff --brief /etc/ntp.conf $TMPFILE > /dev/null
        if [ $? -ne 0 ] ; then
            # tell the user what has changed
            diff /etc/ntp.conf $TMPFILE
            
            # update the original
            sudo cp $TMPFILE /etc/ntp.conf
        fi
        rm $TMPFILE

        sudo ntpdate $ntpserver
    fi

    sudo systemctl start ntp

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install Python Developer Components

There are a collection of Python components that are part of the Ubuntu 
repository that are tested to be supported by the specific distribution being
used by this installation.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y gcc make python3-dev python3-setuptools 
    # Check if python3-libpcap is available
    if apt-cache show python3-libpcap >/dev/null 2>&1; then
        sudo apt-get install -y python3-libpcap
    else
        echo "Warning: python3-libpcap package not found. Will attempt to install via pip later."
    fi
elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install Python Modules

There are some additional Python modules that are provided by PyPI.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    # Install Python packages using pip3 instead of easy_install
    sudo pip3 install --upgrade pytz simplejson bottle
    sudo pip3 install --upgrade bacpypes bacpypes3
    sudo pip3 install --upgrade redis lxml
    
    # Install python-libpcap if it wasn't available via apt
    if ! apt-cache show python3-libpcap >/dev/null 2>&1; then
        echo "Installing libpcap Python binding via pip..."
        sudo pip3 install python-libpcap
    fi
elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install XML Developer Components

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y libxslt-dev
    sudo pip3 install lxml
elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install Redis

Redis is a very fast key/value store and serves as the database engine for 
accumulating statistics of various types of traffic.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y redis-server
    sudo pip3 install --upgrade redis
elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== NMAP

The NMAP tool is used in some installations to "sweep" the network looking for 
IP devices so that new devices and changes in MAC addresses can be logged along
with the traffic.  This step is optional, the sweep function has not been 
released yet.

EOF
read -p "Install nmap? [y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y nmap

    # allow users to run without 'sudo'
    sudo chmod u+s /usr/bin/nmap

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Configure BACmon

There is a bundled application that prompts for various configuration parameters
and stores the results in the INI file.  The INI file is not part of the BACmon
distribution.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    # run the configuration helper
    python3 bacmon_config_helper.py || exit 1

    # copy the INI file into place
    sudo -u bacmon cp -v bacmon_ini $BACMON_INI

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

# extract the configuration parameters from the INI file
BACMON_LOGDIR=`cat $BACMON_INI | grep ^logdir: | awk -F:\  '{ print $2 }'`
BACMON_APACHEDIR=`cat $BACMON_INI | grep ^apachedir: | awk -F:\  '{ print $2 }'`
BACMON_STATICDIR=`cat $BACMON_INI | grep ^staticdir: | awk -F:\  '{ print $2 }'`
BACMON_TEMPLATEDIR=`cat $BACMON_INI | grep ^templatedir: | awk -F:\  '{ print $2 }'`

cat << EOF

========== Create/Populate BACmon Home

The BACmon user home directory needs a series of subdirectories created and 
populate with static HTML files, CSS, and Javascript.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    # make a directory for log files and open it up
    if [ ! -d "$BACMON_LOGDIR" ] ;
    then
        sudo -u bacmon mkdir $BACMON_LOGDIR
        sudo -u bacmon chmod +rw $BACMON_LOGDIR
    fi

    # make a directory for the Apache log files
    if [ ! -d "$BACMON_APACHEDIR" ] ;
    then
        sudo -u bacmon mkdir $BACMON_APACHEDIR
        sudo -u bacmon chmod +rw $BACMON_APACHEDIR
    fi

    # make a directory for static files and copy from this source
    if [ ! -d "$BACMON_STATICDIR" ] ;
    then
        sudo -u bacmon mkdir $BACMON_STATICDIR
        sudo -u bacmon chmod +rw $BACMON_STATICDIR
        sudo -u bacmon mkdir $BACMON_STATICDIR/js
        sudo -u bacmon chmod +rw $BACMON_STATICDIR/js
        sudo -u bacmon cp -v ./static/* $BACMON_STATICDIR
        sudo -u bacmon cp -v ./static/js/* $BACMON_STATICDIR/js
    fi

    # make a directory for template files and copy them from this source
    if [ ! -d "$BACMON_TEMPLATEDIR" ] ;
    then
        sudo -u bacmon mkdir $BACMON_TEMPLATEDIR
        sudo -u bacmon chmod +rw $BACMON_TEMPLATEDIR
        sudo -u bacmon cp -v ./template/* $BACMON_TEMPLATEDIR
    fi

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install Apache WSGI

The web presentation tool is a WSGI application, this installation step adds
the WSGI Apache module, copies the BACmon specific Python modules into the 
home directory, then installs and enables the site. The site definition file
was created during the configuration step, it is not part of the BACmon
distribution.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    # Install Python 3 version of mod_wsgi for Apache
    sudo apt-get install -y libapache2-mod-wsgi-py3

    # copy the application
    sudo -u bacmon cp BACmonWSGI.py $BACMON_HOME
    sudo chmod +x $BACMON_HOME/BACmonWSGI.py

    sudo -u bacmon cp XML.py $BACMON_HOME
    sudo -u bacmon cp XHTML.py $BACMON_HOME
    sudo -u bacmon cp timeutil.py $BACMON_HOME

    # copy the site file
    sudo cp bacmon_apache_wsgi /etc/apache2/sites-available/bacmon.conf

    # disable the default site, enable the new one
    sudo a2dissite 000-default || echo "(no default site to disable)"
    sudo a2ensite bacmon

    # restart apache
    sudo systemctl restart apache2

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install Daemonlogger and BACmonLogger

Daemonlogger is an application in the same family of tools as Wireshark and tshark.
It captures raw packets from an interface and archives them in pcap
files (the binary file format shared by these tools).  By pointing it at a 
directory and specifying a rollover value, new files are created.

BACmonLogger is the use of daemonlogger with filters for BACnet traffic on the
standard port (UDP port 47808).  If there is BACnet traffic to be captured and 
analyzed on other ports, this will have to be adjusted.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    sudo apt-get install -y daemonlogger

    # Check if we're using systemd
    if has_systemd; then
        # Create systemd service file for bacmonlogger
        cat > bacmonlogger.service << 'EOL'
[Unit]
Description=BACmonLogger Packet Capture Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/daemonlogger -i any -l /home/bacmon/log -f "port 47808" -c 67108864 -r 10
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        # Install and start the service
        sudo cp bacmonlogger.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable bacmonlogger.service
        sudo systemctl start bacmonlogger.service
        
        echo "BACmonLogger service installed and started using systemd"
    else
        # Use the traditional init script for older systems
        sudo cp bacmonlogger_init /etc/init.d/bacmonlogger
        sudo chmod +x /etc/init.d/bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc0.d/K20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc1.d/K20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc2.d/S20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc3.d/S20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc4.d/S20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc5.d/S20bacmonlogger
        sudo ln -sf /etc/init.d/bacmonlogger /etc/rc6.d/K20bacmonlogger

        # start it now
        sudo /etc/init.d/bacmonlogger start
        
        echo "BACmonLogger service installed and started using init.d script"
    fi

    # install the crontab to purge files
    sudo -u bacmon cp bacmonlogger_purge.sh $BACMON_HOME/
    sudo chmod +x $BACMON_HOME/bacmonlogger_purge.sh
    sudo -u bacmon crontab bacmonlogger_purge.crontab

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

cat << EOF

========== Install BACmon Daemon

The BACmon daemon opens a UDP socket, receives broadcast traffic, decodes the
packets, and analyzes it in various ways storing what it finds in Redis. 
This service will be configured to start automatically.

EOF
read -p "[y/n/x] " yesno || exit 1

if [ "$yesno" = "y" ] ;
then
    # copy the application
    sudo -u bacmon cp BACmon.py $BACMON_HOME

    # For modern Ubuntu (18.04+), use systemd instead of upstart
    if [ -d "/etc/systemd/system" ]; then
        # Create systemd service file
        cat > bacmon.service << 'EOL'
[Unit]
Description=BACmon Service
After=network.target redis-server.service

[Service]
Type=simple
User=bacmon
ExecStart=/usr/bin/python3 /home/bacmon/BACmon.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        # Install and start the service
        sudo cp bacmon.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable bacmon.service
        sudo systemctl start bacmon.service
        
        echo "BACmon service installed and started using systemd"
    else
        # Fall back to upstart for older Ubuntu
        sudo cp bacmon.conf /etc/init/bacmon.conf
        sudo initctl reload-configuration
        sudo start bacmon
        
        echo "BACmon service installed and started using upstart"
    fi

elif [ "$yesno" = "x" ] ;
then
    echo "exit..."
    exit 1
else
    echo "Skipped..."
fi

# Function to verify required Python 3 packages
verify_python_packages() {
    echo "Verifying Python 3 packages..."
    
    # List of required packages
    packages=("pytz" "simplejson" "bottle" "bacpypes" "bacpypes3" "redis" "lxml")
    
    for package in "${packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            echo "✓ $package is installed"
        else
            echo "✗ $package is not installed"
            return 1
        fi
    done
    
    return 0
}

# Add verification of Python packages before service verification
cat << EOF

========== Verifying Python Packages

Checking that all required Python 3 packages are installed...

EOF

verify_python_packages
if [ $? -eq 0 ]; then
    echo "All required Python packages are installed!"
else
    echo "Warning: Some Python packages may not be installed correctly."
    echo "You can try reinstalling them manually using:"
    echo "  sudo pip3 install pytz simplejson bottle bacpypes bacpypes3 redis lxml"
fi

# Function to check service status
check_service_status() {
    local service_name=$1
    echo "Checking $service_name service status..."
    
    if has_systemd; then
        if systemctl is-active --quiet $service_name; then
            echo "✓ $service_name service is running"
            return 0
        else
            echo "✗ $service_name service is not running"
            systemctl status $service_name --no-pager 2>/dev/null || true
            return 1
        fi
    else
        # For non-systemd systems, use status command
        if service $service_name status > /dev/null 2>&1; then
            echo "✓ $service_name service is running"
            return 0
        else
            echo "✗ $service_name service is not running"
            return 1
        fi
    fi
}

# Add final verification of services
cat << EOF

========== Verifying Services

Checking that all required services are running...

EOF

# Check Redis service
check_service_status redis-server
redis_status=$?

# Check Apache service
check_service_status apache2
apache_status=$?

# Check BACmon service
if has_systemd; then
    check_service_status bacmon.service
    bacmon_status=$?
    
    check_service_status bacmonlogger.service
    logger_status=$?
else
    check_service_status bacmon
    bacmon_status=$?
    
    check_service_status bacmonlogger
    logger_status=$?
fi

# Summary
echo
echo "Installation summary:"
echo "--------------------"
echo "Python 3 packages: $(verify_python_packages > /dev/null && echo "✓ Installed" || echo "✗ Issues detected")"
echo "Redis service: $([ $redis_status -eq 0 ] && echo "✓ Running" || echo "✗ Not running")"
echo "Apache service: $([ $apache_status -eq 0 ] && echo "✓ Running" || echo "✗ Not running")"
echo "BACmon service: $([ $bacmon_status -eq 0 ] && echo "✓ Running" || echo "✗ Not running")"
echo "BACmonLogger service: $([ $logger_status -eq 0 ] && echo "✓ Running" || echo "✗ Not running")"
echo

if [ $redis_status -eq 0 ] && [ $apache_status -eq 0 ] && [ $bacmon_status -eq 0 ]; then
    echo "BACmon installation appears to be successful! 🎉"
    echo "You can access the web interface at http://localhost/bacmon/"
else
    echo "Some services are not running. Please check the logs and try to resolve the issues."
    echo "For more information, check the system logs:"
    if has_systemd; then
        echo "  sudo journalctl -u bacmon.service"
        echo "  sudo journalctl -u bacmonlogger.service"
    else
        echo "  sudo tail -n 50 /var/log/syslog"
    fi
fi

cat << EOF

========== Installation Complete ==========

Thank you for installing BACmon! Here's what to do next:

1. Access the web interface at: http://localhost/bacmon/
2. Review the logs if you experience any issues:
   - Application logs: $BACMON_HOME/log/
   - Service logs: Use 'journalctl -u bacmon.service' (systemd)
                  or check /var/log/syslog (older systems)

For more information, visit the BACmon documentation or
contact support for assistance.

EOF


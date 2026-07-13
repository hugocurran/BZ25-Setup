#! /bin/bash

# Setup the pi from scratch

# Download and install zerotier
curl -s https://install.zerotier.com | sudo bash

# Move the service files first....
sudo cp services/*.service /lib/systemd/system

# Now the executables
sudo cp bin/*.py  bin/*.sh /usr/local/bin

# Setup mavproxy.conf
sudo cp mavproxy.conf /usr/local/etc

# Download HUD2.0 from github and install in /usr/local/bin
git clone https://github.com/hugocurran/hud2.0.git /usr/local/bin/hud

# run the hud setup to download dependencies and setup the venv (in hud/.venv)
# This also installs mavproxy note that everything uses the hud venv
usr/local/bin/hud/setup.sh

echo "Everything is now installed but not setup"
echo
echo "On first use run /usr/local/bin/config.sh to setup the environment"
echo
echo "Note that a solid LED indicates the system is running; a blinking LED"
echo "means that Zerotier is running and connected"
echo
echo "good luck"

echo >/etc/motd <<EOL
BZ25 Compute system

This system has all of the software installed.

You need to run sudo /usr/local/bin/config.sh to setup zerotier and get all the software to start 
automagically when the system boots.

EOL

echo
echo "Rebooting in 10 seconds"
sleep 10
sudo reboot


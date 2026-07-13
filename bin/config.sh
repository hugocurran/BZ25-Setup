#! /bin/bash

ZTDIR=/var/lib/zerotier-one

echo "BZ25 Configuration"
echo
if (( $EUID != 0 )); then 
    echo "Please run as root or use sudo." 
    exit 1 
fi
echo
echo "Zeronet-One configuration…."

# Leave any existing ZT network
# Note that the zerotier-cli json output is wrapped in [] so python treats it as a list
NET=$(zerotier-cli listnetworks | awk 'NR==2 {print $3}')
if [ -z $NET ]; 
	then echo "Not joined to any network";
	else zerotier-cli leave $NET;
fi

# Stop the zerotier-one service and delete the credentials
systemctl stop zerotier-one

rm -f $ZTDIR/identity.public $ZTDIR/identity.secret $ZTDIR/authtoken.secret

# Get the new network ID from the user
read -p "Enter Zerotier-One network ID: " zt_id

# Set new node credentials
zerotier-idtool  generate $ZTDIR/identity.secret $ZTDIR/identity.public

# Configure the network mappings so we know the interface name
# get around well known permission problem using tee
echo "$(zt_id)=zt0" | sudo tee /var/lib/zerotier-one/devicemap > /dev/null

# Restart the zerotier service
systemctl start zerotier-one
systemctl --no-pager status zerotier-one

# Request to join the network
zerotier-cli join $zt_id

# Setup the other services
# mavproxy
echo
echo "Setting up Mavlink forwarding…"
echo "You can connect to this system via TCP, or have UDP packets forwarded to GCS"
while true; do
	read -p "Enter TCP or UDP: " resp
	case "$resp" in
		"TCP")
			MAV_PROTO=$resp
			break;;
			
		"UDP")
			MAV_PROTO=$resp
			read -p "IP address of GCS: " GCS_IP
			break;;
			
		*)
			echo "What?? Try again…"
	esac
done

# write the results to the conf file
cat >/usr/local/etc/mavproxy.conf <<EOL
[mavproxy]
gcs-connection=$MAV_PROTO
gcs-udp=$GCS_IP
EOL

echo "Enabling mavproxy"
systemctl daemon-reload
systemctl enable mavproxy.service

# video stream
echo "Enabling video stream"
systemctl enable hud-generator.service

sudo echo >/etc/motd <<EOL
BZ25 Compute System

This system has been configured to:
	connect to starlink using eth0
	connect to Zerotier using zt0
	start mavproxy: connect using TCP:<zerotierIP>:5760 on the GCS
	start hud-generator: access using srt://<zerotierIP>:9000

To check that Starlink and Zerotier are connected use ifconfig (eth0 and zt0 should have IP addresses).
If the zt0 interface is up and has an IP address the LED should be flashing.
EOL

# Reboot time
echo
echo "System will reboot in 10 seconds"
sleep 10
reboot


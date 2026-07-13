#!/bin/bash
INTERFACE=zt0

# 1. Block execution until zt0 exists and has an IP address assigned 
# 2. Extract that specific IPv4 address and inject it into $ZTIER_IP
while ! ip -4 addr show dev $INTERFACE 2>/dev/null | grep -q "inet" ; do \ 
        echo "Waiting for $INTERFACE  interface and IP address..."; \
       sleep 2;\ 
done  

ZTIER_IP=$(ip -4 addr show dev $INTERFACE | grep -oP '(?<=inet )\d+(\.\d+){3}' | head -n1)

# Read the config file to see which protocol is used
#source <(grep -E '^[A-Za-z_][A-Za-z0-9]*=' /etc/mavproxy.conf)
source <(grep = /etc/mavproxy.conf)

echo $GCS_CONNECTION
echo $GCS_UDP

# Join the user to the dialout group
#usermod -a -G dialout pi

# Execute MAVproxy with the appropriate setup
# Note that we have to use python from the virtual environment

VIRTUAL_ENV=/home/pi/venv
PYTHON_VENV=/home/pi/venv/bin/python3

if [[ "$GCS_CONNECTION" == "TCP" ]]; then
       exec $PYTHON_VENV ${VIRTUAL_ENV}/bin/mavproxy.py --master=/dev/ttyS0 --baudrate=57600 \
	     --out=tcpin:$ZTIER_IP:5760 \
	     --out=udp:127.0.0.1:14551 \
	     --daemon;
elif [[ "$GCS_CONNECTION" == "UDP" ]]; then
	exec $(PYTHON_VENV) ${VIRTUAL_ENV}/bin/mavproxy.py --master=/dev/serial0 --baudrate=57600 \
	     --out=udp:$GCS_UDP:14550 \
	     --out=udp:127.0.0.1:14551 \
	     --daemon;
else
	echo "bugger"
	echo $GCS_CONNECTION
	echo $GCS_UDP
	exit 1;
fi


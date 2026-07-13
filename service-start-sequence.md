This is the sequence for starting services

status-led.service
	Solid light until zerotier starts and has IP address
	Blinking light once zerotier configured
	|
	|
	^
zerotier-one.service
	Waits for eth0 (starlink) to have an IP address
	Depends on a previous join and config of zt0 interface
	|
	|
	^
mavproxy.service
	Waits for zt0 to have an IP address
	Outputs on udp:<zt0 address>:14550 --> GCS
	Outputs on udp:127.0.0.1:14551 -> HUD2.0
	|
	|
	^
hud2_0.service
	Waits for mavproxy.service
	Outputs on srt://<zt0 address>:9000


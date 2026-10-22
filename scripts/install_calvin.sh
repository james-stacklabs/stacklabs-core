cat << 'SERVICE' > /tmp/sovereign-cam.service
[Unit]
Description=Sovereign OS Argus Edge Camera Daemon
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/james/stacklabs/scripts/edge_cam.py
WorkingDirectory=/home/james/stacklabs/scripts
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=sovereign-cam
User=james
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

mv /tmp/sovereign-cam.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sovereign-cam.service
systemctl start sovereign-cam.service

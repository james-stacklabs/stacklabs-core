#!/bin/bash
nmcli connection add type wifi con-name "pixel_7_hotspot" ifname wlan0 ssid "pixel_7_hotspot"
nmcli connection modify "pixel_7_hotspot" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "!!Stella1977"
nmcli connection modify "pixel_7_hotspot" connection.autoconnect yes
nmcli connection modify "pixel_7_hotspot" connection.autoconnect-priority 10

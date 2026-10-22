#!/bin/bash
matchbox-window-manager -use_titlebar no -use_cursor yes &
/usr/bin/chromium-browser --no-sandbox --ignore-certificate-errors --kiosk --disable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL --force-device-scale-factor=1.5 'https://localhost:3000/?domain=MLB&room=starter'

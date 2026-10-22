import os

# Search for metsy_soaked_rain.png or similar in SovereignOS
for root, dirs, files in os.walk("/home/james/stacklabs"):
    for file in files:
        if 'metsy_soaked_rain' in file or 'barb_avatar' in file:
            print(os.path.join(root, file))

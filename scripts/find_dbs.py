import os

for root, dirs, files in os.walk("/home/james/stacklabs"):
    for file in files:
        if file.endswith(".db"):
            print(os.path.join(root, file))

for root, dirs, files in os.walk("/home/james/sovereign_inbox"):
    for file in files:
        if file.endswith(".db"):
            print(os.path.join(root, file))

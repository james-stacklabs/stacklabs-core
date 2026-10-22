#!/bin/bash
# Sync sovereign_now.db from Node .73 to Calvin (.115)
rsync -avz /home/james/stacklabs/sovereign_now.db james@192.168.1.115:/home/james/stacklabs/sovereign_now.db

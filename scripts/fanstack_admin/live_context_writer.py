import os
from datetime import datetime

CONTEXT_LOG = '/home/james/stacklabs/scripts/fanstack_live_context.txt'

def append_live_context(context_string, source="API"):
    """
    Appends structured context events to the fanstack_live_context.txt file.
    Does nothing if context_string is empty.
    """
    if not context_string:
        return
        
    try:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [SOURCE: {source}] : {context_string}\n"
        
        with open(CONTEXT_LOG, 'a') as f:
            f.write(log_entry)
            
        print(f"[CONTEXT WRITER] Injected temporal context overlay: {context_string[:50]}...")
        
    except Exception as e:
        print(f"[ERROR] Live Context Writer Failed: {e}")
        raise

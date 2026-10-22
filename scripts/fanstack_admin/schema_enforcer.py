import json

def validate_payload(payload):
    """
    Validates an incoming JSON configuration payload against the expected 
    FanStack override and protocol structure.
    """
    required_keys = ["source", "target_nodes", "new_state", "instructions", "constraints_toggle", "global_context"]
    
    # Missing key check
    for key in required_keys:
        if key not in payload:
            raise ValueError(f"Schema Validation Error: Missing required key '{key}'")
            
    # Constraints toggle validation
    if not isinstance(payload.get("constraints_toggle"), dict):
         raise ValueError("Schema Validation Error: 'constraints_toggle' must be a dictionary")
         
    if "action" not in payload["constraints_toggle"] or "protocol_string" not in payload["constraints_toggle"]:
         raise ValueError("Schema Validation Error: 'constraints_toggle' must contain 'action' and 'protocol_string'")

    if payload["constraints_toggle"]["action"] not in ["inject", "strip", "none"]:
        raise ValueError("Schema Validation Error: 'action' must be 'inject', 'strip', or 'none'")

    return True

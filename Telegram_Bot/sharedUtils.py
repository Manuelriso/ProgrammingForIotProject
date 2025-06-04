######## FUNCTIONS SHARED BETWEEN BOT AND ALERTNOTIFIER #########
## TO AVOID CIRCULAR IMPORTS.

### Normalize values to integers
def normalize_state_to_int(value):
    try:
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ("on", "1"):
                return 1
            if value in ("off", "0"):
                return 0
            return int(float(value))
        return int(value)
    except (ValueError, TypeError) as e:
        print(f"[!] Error normalizing the value: {value} - {e}")
        raise

### Normalize values to strings for display
def normalize_state_to_str(value): 
    value = str(value).strip().lower()
    if value in ["1", "on", "true"]:
        return "ON"
    elif value in ["0", "off", "false"]:
        return "OFF"
    else:
        return "OFF" #Just as prevention
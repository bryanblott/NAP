import utime

def log_with_timestamp(message):
    timestamp = utime.ticks_ms()
    print(f"[{timestamp}] {message}")
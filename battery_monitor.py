#!/usr/bin/python
import smbus2 as smbus
import time
import os

# Define constants
I2C_BUS = 1
I2C_ADDRESS = 0x36  # Correct address for X1203 UPS HAT
CHECK_INTERVAL = 10  # Check battery every 10 seconds
CHARGE_THRESHOLD = 20  # Alert when battery below 20%
SHUTDOWN_DELAY = 60  # Shutdown after 60 seconds when critical

def get_battery_info():
    try:
        bus = smbus.SMBus(I2C_BUS)
        
        # Calculate current charge
        msb = int(bus.read_byte_data(I2C_ADDRESS, 0x04))
        lsb = int(bus.read_byte_data(I2C_ADDRESS, 0x05))
        capacity = msb + lsb / 255.0
        
        # Determine if charging or discharging
        state = "charging" if is_charging(bus) else "discharging"
        
        print(f"Battery capacity: {capacity:.2f}% ({state})")
        
        # Critical battery check
        if capacity < CHARGE_THRESHOLD and state == "discharging":
            print(f"WARNING: Battery level critical ({capacity:.2f}%)")
            print(f"System will shutdown in {SHUTDOWN_DELAY} seconds unless power is connected")
            # Uncomment the line below to enable actual shutdown
            # os.system(f"sudo shutdown -h +1 'Critical battery level ({capacity:.2f}%)'")
        
        return capacity, state
        
    except Exception as e:
        print(f"Error reading battery info: {e}")
        print("Make sure the UPS HAT is properly connected and I2C is enabled")
        print("Try adjusting the pogo pins for better contact with the Raspberry Pi 5")
        return None, None

def is_charging(bus):
    # This is a simplified check - may need adjustment based on actual register values
    try:
        status_reg = bus.read_byte_data(I2C_ADDRESS, 0x00)
        return (status_reg & 0x40) != 0  # Check charging bit
    except:
        return False

if __name__ == "__main__":
    print("Geekworm X1203 UPS HAT Battery Monitor")
    print("--------------------------------------")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            get_battery_info()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")

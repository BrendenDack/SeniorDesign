#!/usr/bin/python
import smbus2 as smbus
import time
import psutil  # Requires `pip install psutil`

# Constants
I2C_BUS = 1
I2C_ADDRESS = 0x36  # X1203 UPS HAT I2C address
SAMPLE_RATE = 0.2   # 5 samples per second
SAMPLES = 5
CHARGE_THRESHOLD = 20
BATTERY_CAPACITY_AH = 10.0  # Updated to 10Ah (10000mAh)
BASE_CURRENT_A = 2.7        # Pi 5 idle current
MAX_CURRENT_A = 5.5         # Pi 5 max current under heavy load

# Function to estimate current based on CPU load
def estimate_current(is_powered):
    if is_powered:
        return 0.0, 0.0  # No current draw from battery when charging
    cpu_percent = psutil.cpu_percent(interval=0.1)
    current = BASE_CURRENT_A + (MAX_CURRENT_A - BASE_CURRENT_A) * (cpu_percent / 100.0)
    return current, cpu_percent

# Function to get battery info
def get_battery_info(bus, start_time=None, initial_capacity=None):
    try:
        # Read capacity
        msb = bus.read_byte_data(I2C_ADDRESS, 0x04)
        lsb = bus.read_byte_data(I2C_ADDRESS, 0x05)
        capacity = msb + lsb / 255.0

        # Read status from register 0x02
        status = bus.read_byte_data(I2C_ADDRESS, 0x02)
        print(f"Debug - Status register 0x02: 0x{status:02X}")

        # Use bit 6 for power state
        is_powered = (status & 0x40) != 0
        state = "discharging" if not is_powered else "charging"

        # Estimate current based on system load
        current, cpu_percent = estimate_current(is_powered)

        # Estimate remaining time when discharging
        remaining_time = None
        measured_rate = None
        if state == "discharging" and current > 0:
            remaining_capacity_ah = (capacity / 100.0) * BATTERY_CAPACITY_AH
            remaining_time = (remaining_capacity_ah / current) * 60  # Minutes
            if start_time and initial_capacity:
                elapsed_hours = (time.time() - start_time) / 3600
                capacity_drop = initial_capacity - capacity
                if elapsed_hours > 0 and capacity_drop > 0:
                    measured_rate = (capacity_drop / 100.0 * BATTERY_CAPACITY_AH) / elapsed_hours

        return capacity, current, state, remaining_time, cpu_percent, measured_rate
    except Exception as e:
        print(f"Error reading battery info: {e}")
        return None, None, None, None, None, None

# Format output
def format_output(capacity, current, state, remaining_time, cpu_percent, measured_rate):
    output = f"{capacity:.2f}% battery, {current:.2f}A current ({state}, CPU {cpu_percent:.1f}%)"
    if remaining_time is not None:
        hours = int(remaining_time // 60)
        minutes = int(remaining_time % 60)
        output += f"\nest. {hours}h {minutes}m battery remaining"
        if measured_rate:
            output += f"\nMeasured discharge rate: {measured_rate:.2f} Ah/h"
    return output

# Main execution
if __name__ == "__main__":
    print("Geekworm X1203 UPS HAT Battery Monitor")
    print("--------------------------------------")
    try:
        bus = smbus.SMBus(I2C_BUS)
        start_time = None
        initial_capacity = None

        for i in range(SAMPLES):
            capacity, current, state, remaining_time, cpu_percent, measured_rate = get_battery_info(
                bus, start_time, initial_capacity
            )
            if capacity is not None:
                if i == 0 and state == "discharging":
                    start_time = time.time()
                    initial_capacity = capacity
                print(format_output(capacity, current, state, remaining_time, cpu_percent, measured_rate))
                if capacity < CHARGE_THRESHOLD and state == "discharging":
                    print(f"WARNING: Battery level critical ({capacity:.2f}%)")
            time.sleep(SAMPLE_RATE)

        print("Monitoring complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        print("Check UPS HAT connection and I2C enablement")
import json
import struct
import subprocess
import logging
import smbus2
from gpiozero import Button
from gpiozero.exc import GPIOZeroError

# Constants
I2C_BUS_ID = 1
I2C_ADDRESS = 0x36
CHARGE_STATE_PIN = 6  # GPIO pin for charge state detection
BATTERY_CAPACITY_MAH = 10000  # UPS battery spec

# Setup logging to same file as menu_renderer
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='menu_renderer.log',
    filemode='a'
)

class BatteryMonitor:
    def __init__(self, use_gpio=True):
        self.bus = None
        self.pld_button = None
        self.use_gpio = use_gpio
        try:
            self.bus = smbus2.SMBus(I2C_BUS_ID)
            logging.info("I2C bus initialized")
        except Exception as e:
            logging.error(f"Failed to initialize I2C bus: {e}")
            self.bus = None
        if use_gpio:
            try:
                self.pld_button = Button(CHARGE_STATE_PIN, pull_up=False, bounce_time=0.2)
                logging.info("Charge state GPIO initialized")
            except GPIOZeroError as e:
                logging.error(f"Failed to initialize charge state GPIO: {e}")
                self.pld_button = None

    def read_voltage_and_capacity(self):
        if not self.bus:
            logging.error("I2C bus not available")
            return None, None
        try:
            voltage_read = self.bus.read_word_data(I2C_ADDRESS, 2)
            capacity_read = self.bus.read_word_data(I2C_ADDRESS, 4)
            voltage = struct.unpack("<H", struct.pack(">H", voltage_read))[0] * 1.25 / 1000 / 16
            capacity = struct.unpack("<H", struct.pack(">H", capacity_read))[0] / 256
            logging.debug(f"Battery: voltage={voltage:.2f}V, capacity={capacity:.1f}%")
            return voltage, capacity
        except Exception as e:
            logging.error(f"Failed to read I2C data: {e}")
            return None, None

    def read_hardware_metric(self, command_args, strip_chars):
        try:
            output = subprocess.check_output(command_args).decode("utf-8")
            metric_str = output.split("=")[1].strip().rstrip(strip_chars)
            metric = float(metric_str)
            logging.debug(f"Hardware metric {command_args}: {metric}")
            return metric
        except Exception as e:
            logging.error(f"Failed to read hardware metric {command_args}: {e}")
            return None

    def read_cpu_temp(self):
        return self.read_hardware_metric(["vcgencmd", "measure_temp"], "'C")

    def read_cpu_volts(self):
        return self.read_hardware_metric(["vcgencmd", "pmic_read_adc", "VDD_CORE_V"], 'V')

    def read_cpu_amps(self):
        return self.read_hardware_metric(["vcgencmd", "pmic_read_adc", "VDD_CORE_A"], 'A')

    def read_power_draw(self):
        try:
            output = subprocess.check_output(['vcgencmd', 'pmic_read_adc']).decode("utf-8")
            lines = output.split('\n')
            volts, amps = {}, {}
            for line in lines:
                if not line.strip():
                    continue
                parts = line.strip().split()
                label, value = parts[0], parts[-1]
                val = float(value.split('=')[1][:-1])
                short_label = label[:-2]
                if label.endswith('A'):
                    amps[short_label] = val
                elif label.endswith('V'):
                    volts[short_label] = val
            wattage = sum(amps[k] * volts[k] for k in amps if k in volts)
            logging.debug(f"System power draw: {wattage:.2f}W")
            return wattage
        except Exception as e:
            logging.error(f"Failed to read power draw: {e}")
            return None

    def estimate_runtime_minutes(self, capacity_percent, current_draw_amps):
        try:
            if capacity_percent is None or current_draw_amps is None:
                return None
            remaining_mah = BATTERY_CAPACITY_MAH * (capacity_percent / 100)
            remaining_wh = (remaining_mah / 1000) * 3.7
            estimated_runtime = (remaining_wh / (current_draw_amps * 5)) * 60
            logging.debug(f"Estimated runtime: {estimated_runtime:.1f} minutes")
            return round(estimated_runtime, 1)
        except Exception as e:
            logging.error(f"Failed to estimate runtime: {e}")
            return None

    def get_battery_status(self, voltage, power_state):
        if voltage is None:
            return "Unknown"
        if power_state == "Plugged In":
            return "Charging" if 3.4 <= voltage <= 4.2 else "Unknown"
        if 3.87 <= voltage <= 4.2:
            return "Full"
        elif 3.7 <= voltage < 3.87:
            return "High"
        elif 3.55 <= voltage < 3.7:
            return "Medium"
        elif 3.4 <= voltage < 3.55:
            return "Low"
        elif voltage < 3.4:
            return "Critical"
        return "Unknown"

    def detect_power_state(self):
        if not self.use_gpio or not self.pld_button:
            logging.warning("Charge state GPIO not available")
            return "Unknown"
        try:
            state = "Plugged In" if not self.pld_button.is_pressed else "Battery"
            logging.debug(f"Power state: {state}")
            return state
        except Exception as e:
            logging.error(f"Failed to detect power state: {e}")
            return "Unknown"

    def get_battery_info(self):
        voltage, capacity = self.read_voltage_and_capacity()
        power_state = self.detect_power_state()
        status = self.get_battery_status(voltage, power_state)
        capacity_percent = round(capacity, 1) if capacity is not None else 0.0
        return (status, capacity_percent)

    def get_system_status(self):
        voltage, capacity = self.read_voltage_and_capacity()
        cpu_temp = self.read_cpu_temp()
        cpu_voltage = self.read_cpu_volts()
        cpu_current = self.read_cpu_amps()
        power_watts = self.read_power_draw()
        power_state = self.detect_power_state()
        battery_status = self.get_battery_status(voltage, power_state)
        runtime_est = self.estimate_runtime_minutes(capacity, cpu_current) if capacity and cpu_current else None
        icon_map = {
            "Full": "battery_full.png",
            "High": "battery_high.png",
            "Medium": "battery_medium.png",
            "Low": "battery_low.png",
            "Critical": "battery_critical.png",
            "Unknown": "battery_critical.png",
            "Charging": "battery_charging.png"
        }

        return {
            "battery": {
                "voltage": round(voltage, 2) if voltage else None,
                "capacity_percent": round(capacity, 1) if capacity else None,
                "status": battery_status,
                "icon": icon_map.get(battery_status, "battery_critical.png")
            },
            "estimated_runtime_minutes": runtime_est,
            "power_state": power_state,
            "system_power": {
                "system_power_watts": round(power_watts, 2) if power_watts else None,
                "cpu_metrics": {
                    "cpu_temp_c": round(cpu_temp, 1) if cpu_temp else None,
                    "cpu_voltage_v": round(cpu_voltage, 2) if cpu_voltage else None,
                    "cpu_current_a": round(cpu_current, 2) if cpu_current else None
                }
            }
        }

    def cleanup(self):
        try:
            if self.bus:
                self.bus.close()
                logging.info("I2C bus closed")
        except Exception as e:
            logging.error(f"Failed to close I2C bus: {e}")
        if self.use_gpio and self.pld_button:
            try:
                self.pld_button.close()
                logging.info("Charge state GPIO closed")
            except Exception as e:
                logging.error(f"Failed to close charge state GPIO: {e}")

def setup_battery_monitor(use_gpio=True):
    return BatteryMonitor(use_gpio=use_gpio)

_monitor = setup_battery_monitor(use_gpio=True)

def get_battery_info():
    return _monitor.get_battery_info()

def is_charging():
    status, _ = _monitor.get_battery_info()
    return status == "Charging"
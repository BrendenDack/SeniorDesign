import time
import spidev
import logging
from gpiozero import LED, PWMLED
import numpy as np

class RaspberryPi:
    def __init__(self, spi=spidev.SpiDev(0, 0), spi_freq=40000000, rst=27, dc=25, bl=18, bl_freq=1000, i2c=None, i2c_freq=100000):
        self.np = np
        self.RST_PIN = rst
        self.DC_PIN = dc
        self.BL_PIN = bl
        self.SPEED = spi_freq
        self.BL_freq = bl_freq

        # GPIO pin control using gpiozero
        self.rst_pin = LED(self.RST_PIN)
        self.dc_pin = LED(self.DC_PIN)
        self.bl_pwm = PWMLED(self.BL_PIN, frequency=self.BL_freq)
        self.bl_pwm.value = 1.0  # Set initial brightness to 100%

        # Initialize SPI
        self.SPI = spi
        if self.SPI is not None:
            self.SPI.max_speed_hz = self.SPEED
            self.SPI.mode = 0b00

    def digital_write(self, pin, value):
        if pin == self.RST_PIN:
            self.rst_pin.value = value
        elif pin == self.DC_PIN:
            self.dc_pin.value = value
        elif pin == self.BL_PIN:
            self.bl_pwm.value = float(value)

    def digital_read(self, pin):
        if pin == self.RST_PIN:
            return self.rst_pin.value
        elif pin == self.DC_PIN:
            return self.dc_pin.value
        elif pin == self.BL_PIN:
            return self.bl_pwm.value
        return 0

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        if self.SPI is not None:
            self.SPI.writebytes(data)

    def bl_DutyCycle(self, duty):
        # `duty` is expected to be 0–100; convert to 0.0–1.0
        self.bl_pwm.value = duty / 100.0

    def bl_Frequency(self, freq):
        self.bl_pwm.frequency = freq

    def module_init(self):
        # Reset PWM LED settings just in case
        self.bl_pwm.frequency = self.BL_freq
        self.bl_pwm.value = 1.0

        if self.SPI is not None:
            self.SPI.max_speed_hz = self.SPEED
            self.SPI.mode = 0b00
        return 0

    def module_exit(self):
        logging.debug("spi end")
        if self.SPI is not None:
            self.SPI.close()

        logging.debug("gpio cleanup...")
        self.rst_pin.on()
        self.dc_pin.off()
        self.bl_pwm.off()
        time.sleep(0.001)
        self.bl_pwm.on()  # Backlight back on for clean exit

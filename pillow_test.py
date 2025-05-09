from PIL import Image, ImageDraw, ImageFont
from firmware.LCD_2inch4_gpiozero import LCD_2inch4

LCD = LCD_2inch4()
LCD.Init()
LCD.clear()


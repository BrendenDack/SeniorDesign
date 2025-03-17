# python script showing battery details 
import psutil 
  
# function returning time in Hour:Min 
def convertTime(seconds): 
    hours, minutes = divmod(minutes, 60) 
    return "%d:%02d" % (hours, minutes) 
  
# returns a tuple 
battery = psutil.sensors_battery() 
  
print("Battery percentage : ", battery.percent) 
print("Power plugged in : ", battery.power_plugged) 
  
# converting seconds to hh:mm:ss 
print("Battery left : ", convertTime(battery.secsleft)) 

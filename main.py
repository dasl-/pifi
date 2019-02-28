import serial
import time
import random

arduino = serial.Serial('/dev/cu.usbmodem1411', 115200, timeout=100)
time.sleep(5)
count = 0
start = time.time()

def writeToArduino(data):
  print(data)
  arduino.write((data + "\n").encode())
  time.sleep(.04)
  # # break into substrings
  # n = 10
  # for i in range(0, len(data), n):
  #   arduino.write((data[i:i + n]).encode())

while True:
  # arduino.write("0,0:255,0,0&0,1:0,0,255&")
  red = 50
  # sleeptime = .04;
  # sleeptime = .01;
  sleeptime = 5;

  while (red < 255):
    # color = str(red)+","+str(red)+","+str(red)

    # data = "0,0:255,0,0&0,1:255,0,0&"
    # data = ""
    for row in range(0,6):
      red += 5
      data = ""
      data += str(row) + ":"
      for i in range (0,30):
        data += str(random.randint(50,255)) + "&"
        # data += str(red) + "&"
      writeToArduino(data);
      time.sleep(sleeptime)
      # data += "\n"

    # start = time.time()
    # writeToArduino(data);
    # print((time.time() - start)*1000)

    red = red + 30
    time.sleep(sleeptime)

  #data = arduino.readline()[:-2] #the last bit gets rid of the new-line chars
  #if data:
  #  print data
  # 0:255&123&23&
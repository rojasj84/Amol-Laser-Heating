import serial

s = serial.Serial('COM5')
res = s.read()
print(res)

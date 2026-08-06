import serial
import time
# Library with functions to talk with the agilis piezo motion controller

#Set comport for agilis
COMPORT = 'COM10'

def pz_travel_PR(comport,chan,axis,direction,steps):

    str_intruct = str(axis) + "PR"

    if(direction == 0):
        str_intruct = str_intruct + "-" + str(steps)
    else:
        str_intruct = str_intruct + str(steps)

    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)
    ser.write( b'CC' + str(chan).encode('ascii') +  b'\r\n')
    ser.write( str_intruct.encode('ascii') +  b'\r\n')
    ser.close()

def pz_travel_JA(comport,chan,axis,speed):

    str_intruct = str(axis) + "JA"
    str_intruct = str_intruct + str(speed)
    #print(str_intruct)
    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    # Perform check for active serial, wait while active
    time.sleep(.01)
    ser.write( b'CC' + str(chan).encode('ascii') +  b'\r\n')
    time.sleep(.01)
    ser.write( str_intruct.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Jog Move at a certain speed

def pz_travel_ST(comport,chan,axis):

    str_intruct = str(axis) + "ST"
    #print(str_intruct)
    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    # Perform check for active serial, wait while active
    time.sleep(.01)
    ser.write( b'CC' + str(chan).encode('ascii') +  b'\r\n')
    time.sleep(.01)
    ser.write( str_intruct.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Stop

def pz_RemoteMode():

    str_intruct = "MR"
    #print(str_intruct)
    ser = serial.Serial(COMPORT,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    ser.write( str_intruct.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Stop

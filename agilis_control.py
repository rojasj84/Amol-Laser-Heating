import serial
import time
# Library with functions to talk with the agilis piezo motion controller

#Set comport for agilis
COMPORT = 'COM10'

# Newport AGILIS command "PR" (Position Relative): move a set number of steps
def piezo_move_relative(comport,channel,axis,direction,steps):

    command_string = str(axis) + "PR"

    if(direction == 0):
        command_string = command_string + "-" + str(steps)
    else:
        command_string = command_string + str(steps)

    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)
    ser.write( b'CC' + str(channel).encode('ascii') +  b'\r\n')
    ser.write( command_string.encode('ascii') +  b'\r\n')
    ser.close()

# Newport AGILIS command "JA" (Jog At speed): move continuously until stopped
def piezo_jog_at_speed(comport,channel,axis,speed):

    command_string = str(axis) + "JA"
    command_string = command_string + str(speed)
    #print(command_string)
    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    # Perform check for active serial, wait while active
    time.sleep(.01)
    ser.write( b'CC' + str(channel).encode('ascii') +  b'\r\n')
    time.sleep(.01)
    ser.write( command_string.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Jog Move at a certain speed

# Newport AGILIS command "ST" (Stop): halt motion on the given axis
def piezo_stop(comport,channel,axis):

    command_string = str(axis) + "ST"
    #print(command_string)
    ser = serial.Serial(comport,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    # Perform check for active serial, wait while active
    time.sleep(.01)
    ser.write( b'CC' + str(channel).encode('ascii') +  b'\r\n')
    time.sleep(.01)
    ser.write( command_string.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Stop

# Newport AGILIS command "MR" (Set Remote Mode): required before the controller
# will accept computer commands instead of front-panel control
def piezo_set_remote_mode():

    command_string = "MR"
    #print(command_string)
    ser = serial.Serial(COMPORT,
                        921600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    ser.write( command_string.encode('ascii') +  b'\r\n')

    ser.close() # Tells Axis to Stop

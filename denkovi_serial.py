import serial

# Function for sending 2 bytes to alter the state of multiple relays at once
def talktodenk(port, byte1, byte2):
    # sudo chmod a+rw /dev/ttyUSB0
    # Change /dev/ttyUSB0 to COMx in Windows

    # Set connection information
    # port = '/dev/ttyUSB0'
    ser = serial.Serial(port,
                        9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)
    # assuming default settings
    packet = bytearray(2)
    packet[0] = byte1
    packet[1] = byte2
    print(packet)
    ser.write(b'x' + packet + b'//')
    ser.close()

# Function to read in the two bytes for the state of the 16 relays
# 'ask//' is sent and two bytes are sent back
def readdenk(port):
    ser = serial.Serial(port,
                        9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    ser.write(b'ask//')
    # time.sleep(.05)

    buffer1 = ser.read(size=1)
    buffer2 = ser.read(size=1)

    ser.close()

    rel_state1 = [0, 0, 0, 0, 0, 0, 0, 0]
    rel_state2 = [0, 0, 0, 0, 0, 0, 0, 0]

    a = buffer1[0]
    # print(a)
    for i in range(8):
        if a/pow(2, 7-i) >= 1:
            rel_state1[i] = 1
            a = a - pow(2, 7-i)
        else:
            rel_state1[i] = 0
    # print(rel_state1)

    a = buffer2[0]
    # print(a)
    for i in range(8):
        if a/pow(2, 7-i) >= 1:
            rel_state2[i] = 1
            a = a - pow(2, 7-i)
        else:
            rel_state2[i] = 0
    # print(rel_state2)

    rel_state = rel_state1 + rel_state2
    # print(rel_state)
    return rel_state

def readdenk2(port):
    ser = serial.Serial(port,
                        9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    ser.write(b'ask//')
    # time.sleep(.05)

    buffer = ser.read(2)
    # buffer2 = ser.read(size=1)
    
    ser.close()


    # print(rel_state)

    return buffer
    

# Function to flip one relay of the Denkovi
# Accepts the port of the Denkovi and the integer of the relay
def flip_single_relay_status(port, bit):
    relays = readdenk(port)

    # print(relays[bit-1])
    if relays[bit-1] == 1:
        relays[bit-1] = 0
    else:
        relays[bit-1] = 1

    b1_rel = [0, 0, 0, 0, 0, 0, 0, 0]
    b2_rel = [0, 0, 0, 0, 0, 0, 0, 0]

    for i in range(8):
        b1_rel[i] = relays[i]
        b2_rel[i] = relays[i+8]

    byte1 = 0
    byte2 = 0

    for digits in b1_rel:
        byte1 = (byte1 << 1) | digits

    for digits in b2_rel:
        byte2 = (byte2 << 1) | digits

    talktodenk(port, byte1, byte2)

if __name__ == "__main__":
    
    flip_single_relay_status("COM6", 9)
    #flipbit("COM5", 5)
    input_buffer = readdenk2("COM6")

        
    #print(bin(input_buffer[0])[2:].zfill(8))
   #print(bin(input_buffer[1])[2:].zfill(8))



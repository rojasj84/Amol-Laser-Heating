import serial

# Function for sending 2 bytes to alter the state of multiple relays at once
def send_relay_bytes(port, byte1, byte2):
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
def read_denkovi_status(port):
    ser = serial.Serial(port,
                        9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1)

    ser.write(b'ask//')
    # time.sleep(.05)

    low_byte = ser.read(size=1)
    high_byte = ser.read(size=1)

    ser.close()

    low_byte_relay_states = [0, 0, 0, 0, 0, 0, 0, 0]
    high_byte_relay_states = [0, 0, 0, 0, 0, 0, 0, 0]

    remaining_value = low_byte[0]
    for i in range(8):
        if remaining_value/pow(2, 7-i) >= 1:
            low_byte_relay_states[i] = 1
            remaining_value = remaining_value - pow(2, 7-i)
        else:
            low_byte_relay_states[i] = 0

    remaining_value = high_byte[0]
    for i in range(8):
        if remaining_value/pow(2, 7-i) >= 1:
            high_byte_relay_states[i] = 1
            remaining_value = remaining_value - pow(2, 7-i)
        else:
            high_byte_relay_states[i] = 0

    relay_states = low_byte_relay_states + high_byte_relay_states
    return relay_states

# Packs a 16-element list/string of 0/1 relay states into the two bytes
# the Denkovi board expects (relay 1-8 in byte1, relay 9-16 in byte2)
def pack_relay_bytes(relay_states):
    byte1 = 0
    byte2 = 0

    for bit in relay_states[0:8]:
        byte1 = (byte1 << 1) | int(bit)

    for bit in relay_states[8:16]:
        byte2 = (byte2 << 1) | int(bit)

    return byte1, byte2

# Function to flip one relay of the Denkovi
# Accepts the port of the Denkovi and the integer of the relay
def flip_single_relay_status(port, bit):
    relays = read_denkovi_status(port)

    if relays[bit-1] == 1:
        relays[bit-1] = 0
    else:
        relays[bit-1] = 1

    byte1, byte2 = pack_relay_bytes(relays)

    send_relay_bytes(port, byte1, byte2)

# Function to set all 16 relays at once to an absolute state
# Accepts the port of the Denkovi and a 16-element list/string of 0/1
def write_relay_state(port, new_relay_state):
    byte1, byte2 = pack_relay_bytes(new_relay_state)

    send_relay_bytes(port, byte1, byte2)

if __name__ == "__main__":

    flip_single_relay_status("COM6", 9)
    print(read_denkovi_status("COM6"))


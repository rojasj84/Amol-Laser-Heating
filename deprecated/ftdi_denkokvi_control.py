import ftd2xx
import time

class RelayConnect:
    def __init__(self, ftdi_device):
        
        #fprint(ftdi_device)
        self.relay_status = [0,0,0,0,0,0,0,0]   
        self.ftdi_device = ftdi_device
        self.BaudRate = 9600
        self.ftdi_device = ftdi_device

        #self.getRelaystatus()
    
        
    def getRelaystatus(self):
        try:
            self.RelayArray = ftd2xx.openEx(self.ftdi_device)
            #print("Connected to COM"+ str(self.RelayArray.getComPortNumber()))
            self.RelayArray.setBaudRate(self.BaudRate)
            #self.RelayArray.setBitMode(255,1)
            #print("Device Connected.")
        except:
            print("Device cannot be connected to")

        #Return binary array of relay status
        #relay_status_integer = ord(self.RelayArray.read(1))
        #self.RelayArray.resetDevice()
        #print(relay_status_integer)
        #relay_status_binars_string = bin(relay_status_integer)[2:].zfill(8)
        #print(relay_status_binars_string)
        #self.relay_status = [int(bit) for bit in relay_status_binars_string]
        # 
        
        
        string_to_send  = "ask//"     
        # Transmit the bytes
        self.RelayArray.write(string_to_send.encode('utf-8')) 
        #print(self.RelayArray.read(2))

        time.sleep(0.1)
        #print(self.RelayArray.read(2))


    
    def flip_one_relay(self, relay_number):
        #Call function to establish connection and get the status of all relays
        self.getRelaystatus()
        #print(self.relay_status)

        #Flip the bit of the relay that is assocaited with relay number in the relay states array
        #Relay number is bit number + 1, ei: first relay is 1
        if self.relay_status[8-relay_number] == 1:
            self.relay_status[8-relay_number] = 0
        else:
            self.relay_status[8-relay_number] = 1            
        
        #print(self.relay_status)

        #write the new status to the relays
        #Convert array of 1 and 0s to string of 1s and 0s
        relay_status_string = "".join(str(bit) for bit in self.relay_status)
        #print(relay_status_string)

        #Convert to integer value
        relay_status_string_integer = int(relay_status_string, 2)
        
        #Convert to byte literal
        relay_status_byte_literal = relay_status_string_integer.to_bytes(1, 'big')  # Length of 1 byte, big-endian order
        #print(relay_status_byte_literal)
        
        #Write to FTDI Relays
        self.RelayArray.write(relay_status_byte_literal)
        #self.RelayArray.write(b'\x00')
        self.RelayArray.close()
    
    def write_relay_state(self, new_relay_state):
        #Call function to establish connection and get the status of all relays
        #Relay state is relay 1 2 3 4 5 6 7 8
        self.getRelaystatus()
        #new_relay_state.reverse()

        relays_01to08 = new_relay_state[0:8]
        relays_09to15 = new_relay_state[8:16]
        #print(relays_01to08)
        #print(relays_09to15)
        

        #write the new status to the relays
        #Convert array of 1 and 0s to string of 1s and 0s
        relay_status_string1 = "".join(str(bit) for bit in relays_01to08)
        relay_status_string2 = "".join(str(bit) for bit in relays_09to15)
        #print(relay_status_string1)
        #print(relay_status_string2)

        #Convert to integer value
        relay_status_string_integer1 = int(relay_status_string1, 2)
        relay_status_string_integer2 = int(relay_status_string2, 2)
        #print(relay_status_string_integer2)


        #string_to_send  = "off//"     
        byte1 = relay_status_string_integer1#0b00000001
        byte2 = relay_status_string_integer2#0b11000001

        packet = bytearray(2)
        packet[0] = byte1
        packet[1] = byte2

        string_to_send = b'x' + packet + b'//'
        #Transmit the bytes
        self.RelayArray.write(string_to_send) 

        self.RelayArray.close()

if __name__ == "__main__":
    ftdi_list = ftd2xx.listDevices() #Lists out all connected FTDI devices
    print(ftdi_list)
    # Device name is AQ014SBC

    TTLRelays = RelayConnect(ftdi_list[1])

    #print(ftdi_list[1])

    A = [1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0]
    #TTLRelays.flip_one_relay(5)
    TTLRelays.write_relay_state(A)
    #TTLRelays.flip_one_relay(12)

    #print(TTLRelays.getRelaystatus())
    time.sleep(.5)
        

        
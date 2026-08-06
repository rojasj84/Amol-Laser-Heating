import keyboard
import time
 
c  = 0
while (True):
    if keyboard.is_pressed('a'): 
        print('You pressed the "a" key!') 
        c = c + 1
        print(c)
        time.sleep(0.1)
    elif keyboard.is_pressed('b'): 
        break
# Import required libraries
from tkinter import *
from tkinter import filedialog

# Create an instance of tkinter window
win = Tk()
win.geometry("700x300")

# Create a dialog using filedialog function
win.filename=filedialog.askdirectory(initialdir="C:/", title="Select a file")

# Create a label widget
label=Label(win, text="The File you have selected is: " + win.filename, font='Arial 11 bold')
label.pack()

win.mainloop()
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo
from PIL import ImageTk, Image

class App(tk.Tk):
  def __init__(self):
    super().__init__()

    # configure the root window
    self.title('My Awesome App')
    self.geometry('300x500')

    # label
    self.label = ttk.Label(self, text='Hello, Tkinter!')
    self.label.place(x=100,y=100)

    # button
    self.button = ttk.Button(self, text='Click Me')
    self.button['command'] = self.button_clicked
    self.button.place(x=200,y=200)

  def button_clicked(self):
    showinfo(title='Information', message='Hello, Tkinter!')

if __name__ == "__main__":
  app = App()
  app.mainloop()

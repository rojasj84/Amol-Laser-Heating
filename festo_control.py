import tkinter as tk
import denkovi_serial as DenkTalk

#LEFT_SIDE_COMPORT = "COM7"
#RIGHT_SIDE_COMPORT = "COM6"
button_width = 102
button_height = 30

# Create main window of the Festo Controls
'''class FestoControlWindow(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)'''

class FestoControlWindow(tk.Frame):
    def __init__(self, container, left_denkovi_com_port, right_denkovi_com_port):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        self.place(x = 0, y = 0, width = 285, height = 445)

        self.LeftSideControls = LeftSideFrame(self, left_denkovi_com_port)
        self.LeftSideControls.place(x = 2, y = 2)

        self.RightSideControls = RightSideFrame(self, right_denkovi_com_port)
        self.RightSideControls.place(x = 140, y = 2)


# This is the right side of the controls
class RightSideFrame(tk.Frame):
    def __init__(self, parent, right_side_comport):
        tk.Frame.__init__(self, parent)
        self.config(width=140,height=440,bd=2, relief=tk.GROOVE)

        rlabel = tk.Label(self, text="RIGHT SIDE",  anchor='w', font= ('Calibri 18 bold'))
        rlabel.place(x = 8, y = 0, width = 120, height = 25)

        self.right_side_comport = right_side_comport

        R1_RNOTCH = tk.Checkbutton(self, text = "R1 Laser Notch", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,1))
        R1_RNOTCH.place(x=10,y=(button_height+5)*1,width=button_width,height=button_height)

        R2_R4COLM = tk.Checkbutton(self, text = "R2 4 Col Mirr", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,2))
        R2_R4COLM.place(x=10,y=(button_height+5)*2,width=button_width,height=button_height)

        R3_R4COLBS = tk.Checkbutton(self, text = "R3 4 Col BS", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,3))
        R3_R4COLBS.place(x=10,y=(button_height+5)*3,width=button_width,height=button_height)

        R4_RIRIS = tk.Checkbutton(self, text = "R4 Iris", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,4))
        R4_RIRIS.place(x=10,y=(button_height+5)*4,width=button_width,height=button_height)

        R5_RNDF70T = tk.Checkbutton(self, text = "R5 NDF T70", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,5))
        R5_RNDF70T.place(x=10,y=(button_height+5)*5,width=button_width,height=button_height)

        R6_RNDF50T = tk.Checkbutton(self, text = "R6 NDF 50T", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,6))
        R6_RNDF50T.place(x=10,y=(button_height+5)*6,width=button_width,height=button_height)

        R7_RNDF10T = tk.Checkbutton(self, text = "R7 NDF 10T", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,7))
        R7_RNDF10T.place(x=10,y=(button_height+5)*7,width=button_width,height=button_height) 
 
 #       R9_RTO1MLENS = tk.Checkbutton(self, text = "R9 To 1m Lens", command= lambda:DenkTalk.flip_single_relay_status(right_side_comport,9))
 #       R9_RTO1MLENS.place(x=10,y=(button_height+5)*9,width=button_width,height=button_height)

 #       R10_RFROM1MLENS = tk.Checkbutton(self, text = "R10 From 1m Lens", command= lambda:DenkTalk.flip_single_relay_status(right_side_comport,10))
 #       R10_RFROM1MLENS.place(x=10,y=(button_height+10)*10,width=button_width,height=button_height)
 
 #       R89_RTO1MLENS = tk.Checkbutton(self, text = "R8-9 1m Lens", command= lambda:(DenkTalk.flip_single_relay_status(right_side_comport,9), DenkTalk.flip_single_relay_status(right_side_comport,10)))
 #       R89_RTO1MLENS.place(x=10,y=(button_height+7)*8,width=button_width,height=button_height)

        R89_RTO1MLENS = tk.Checkbutton(self, text = "R8-9 1m Lens", anchor='w', command= lambda:(DenkTalk.flip_single_relay_status(self.right_side_comport,8), DenkTalk.flip_single_relay_status(self.right_side_comport,9)))
        R89_RTO1MLENS.place(x=10,y=(button_height+7)*7.5,width=button_width,height=button_height)

        R10_RINGAAS = tk.Checkbutton(self, text = "R10 InGaAs M", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,10))
        R10_RINGAAS.place(x=10,y=(button_height+5)*9,width=button_width,height=button_height)

        R11_NIRF = tk.Checkbutton(self, text = "R11 NIR F", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,11))
        R11_NIRF.place(x=10,y=(button_height+5)*10,width=button_width,height=button_height)

        R12_RRUBYM = tk.Checkbutton(self, text = "R12 RUBY M", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.right_side_comport,12))
        R12_RRUBYM.place(x=10,y=(button_height+5)*11,width=button_width,height=button_height)

# This is the left side of the controls
class LeftSideFrame(tk.Frame):
    def __init__(self, parent, left_side_comport):
        tk.Frame.__init__(self, parent)
        self.config(width=140,height=440,bd=2, relief=tk.GROOVE)

        llabel = tk.Label(self, text="LEFT SIDE", font= ('Calibri 18 bold'))
        llabel.place(x = 8, y = 0, width = 120, height = 25)

        self.left_side_comport = left_side_comport

        L1_LNOTCH = tk.Checkbutton(self, anchor='w', text = "L1 Laser Notch", command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,12))
        L1_LNOTCH.place(x=10,y=(button_height+5)*1,width=button_width,height=button_height)

        L2_L4COLM = tk.Checkbutton(self, text = "L2 4 Col Mirr", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,11))
        L2_L4COLM.place(x=10,y=(button_height+5)*2,width=button_width,height=button_height)

        L3_L4COLBS = tk.Checkbutton(self, text = "L3 4 Col BS", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,10))
        L3_L4COLBS.place(x=10,y=(button_height+5)*3,width=button_width,height=button_height)

        L4_LIRIS = tk.Checkbutton(self, text = "L4 IRIS", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,9))
        L4_LIRIS.place(x=10,y=(button_height+5)*4,width=button_width,height=button_height)

        L5_LNDF70T = tk.Checkbutton(self, text = "L5 NDF T70", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,8))
        L5_LNDF70T.place(x=10,y=(button_height+5)*5,width=button_width,height=button_height)

        L6_LNDF50T = tk.Checkbutton(self, text = "L6 NDF 50T", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,7))
        L6_LNDF50T.place(x=10,y=(button_height+5)*6,width=button_width,height=button_height)

        L7_LNDF10T = tk.Checkbutton(self, text = "L7 NDF10T", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,6))
        L7_LNDF10T.place(x=10,y=(button_height+5)*7,width=button_width,height=button_height)

        L89_LTO1MLENS = tk.Checkbutton(self, text = "L8-9 1m Lens", anchor='w', command= lambda:(DenkTalk.flip_single_relay_status(self.left_side_comport,5), DenkTalk.flip_single_relay_status(self.left_side_comport,4)))
        L89_LTO1MLENS.place(x=10,y=(button_height+7)*7.5,width=button_width,height=button_height)

        L10_RINGAAS = tk.Checkbutton(self, text = "L10 InGaAs M", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,3))
        L10_RINGAAS.place(x=10,y=(button_height+5)*9,width=button_width,height=button_height)

        L11_NIRF = tk.Checkbutton(self, text = "L11 NIR F", anchor='w', command= lambda:DenkTalk.flip_single_relay_status(self.left_side_comport,2))
        L11_NIRF.place(x=10,y=(button_height+5)*10,width=button_width,height=button_height)

"""     L8_RNDF10T = tk.Button(self, text = "LEFT ND FILTER 10T", command= lambda:DenkTalk.flip_single_relay_status(left_side_comport,4))
        L8_RNDF10T.place(x=10,y=(button_height+5)*9,width=button_width,height=button_height)

        L9_RNDF1T = tk.Button(self, text = "LEFT ND FILTER 1T", command= lambda:DenkTalk.flip_single_relay_status(left_side_comport,3))
        L9_RNDF1T.place(x=10,y=(button_height+5)*10,width=button_width,height=button_height)

        L10_RINGAAS = tk.Button(self, text = "LEFT InGaAs M", command= lambda:DenkTalk.flip_single_relay_status(left_side_comport,2))
        L10_RINGAAS.place(x=10,y=(button_height+5)*11,width=button_width,height=button_height)

        L11_TBD = tk.Button(self, text = "TBD", command= lambda:DenkTalk.flip_single_relay_status(left_side_comport,1))
        L11_TBD.place(x=10,y=(button_height+5)*12,width=button_width,height=button_height)

        L12_TBD = tk.Button(self, text = "TDB", command= lambda:DenkTalk.flip_single_relay_status(left_side_comport,1))
        L12_TBD.place(x=10,y=(button_height+5)*12,width=button_width,height=button_height)
"""


if __name__ == "__main__":
     # Begin code with window code
    window = tk.Tk()
    window.title("Festo Control Window")
    window.geometry("280x445")
    window.configure(bg="light gray")

    festo_window = FestoControlWindow(window, "COM7", "COM6")

    window.mainloop()
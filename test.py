import tkinter as tk
from tkinter import StringVar

class Device:
    def __init__(self, web_files_, firmware_files_):
        self.web_files = web_files_
        self.firmware_files = firmware_files_

devices = {
    "NET232Plus" : Device(dict(X6 = "files/NET232pl_6807GC.rom"), dict(WEB1 = "files/NET232pl_webm_1902.cob"))
}

OPTIONS = []

for key in devices:
    OPTIONS.append(key)

def callback(*args):
    device_details = devices[variable.get()]
    print(device_details.web_files)
    print(device_details.firmware_files)

master = tk.Tk()

variable = StringVar(master)
variable.set(OPTIONS[0]) # default value
variable.trace("w", callback)
w = tk.OptionMenu(master, variable, *OPTIONS)
w.pack()

master.mainloop()

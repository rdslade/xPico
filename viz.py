# Imports
import subprocess
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import IntVar, StringVar
from time import sleep
import serial
import sys
import os
import time
import datetime
import threading
from multiprocessing import Queue, Process
import re
import ipaddress
import telnetlib
import urllib.request
from tkinter.filedialog import askopenfilename

gridColor = "#20c0bb"
HEADER = "#FF69B4"
OKGREEN = "#00ff00"
INTERMEDIATE = "#9a4ce8"
FAILRED = "#ff0000"
STATUSBLUE = "#0000ff"
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def success_str(str):
        return bcolors.OKGREEN + str + bcolors.ENDC

    def fail_str(str):
        return bcolors.FAIL + str + bcolors.ENDC

    def header_str(str):
        return bcolors.HEADER + str + bcolors.ENDC

    def intermediate_str(str):
        return bcolors.OKBLUE + str + bcolors.ENDC

    def underline_str(str):
        return bcolors.UNDERLINE + str + bcolors.ENDC

timeoutMessage = "TIMED OUT WAITING FOR xPICO...EXITING"

### Helper function for reading serial words
def readSerialWord(ser_port):
    char = '0'
    response = ""
    # Continue reading word until not more chars
    while char != '':
        char = ser_port.read().decode()
        response += char
    return response

def waitForResponse(port, timeout = 15, input = "", until = "something"):
    response = ""
    start = time.time()
    while response == "" and time.time() - start < timeout:
        if input != "":
            port.write(input.encode())
        typePort = str(type(port))
        if "Serial" in typePort:
            response = readSerialWord(port)
        elif "Telnet" in typePort:
            response = port.read_until(until.encode(), timeout).decode()
    return response

def exitOnResponse(response, message, failLabel, exitSeq = ""):
    if response == exitSeq:
        addLabelToFrame(failLabel, message, FAILRED)
        return 1
    else:
        return 0

class Station:
    def __init__(self, parent_, com_):
        self.com = com_
        self.ser = serial.Serial(self.com, baudrate = 9600, timeout = .1)
        self.mac = self.ipa = ""
        self.thread = threading.Thread(target = self.process)
        self.frame = tk.Frame(parent_)
        self.initComponents()
        self.packObjects()

    ### Creates the components associated with a single Station instance
    def initComponents(self):
        self.setup = tk.Frame(self.frame)
        self.out = tk.Frame(self.setup)


        self.station_label = tk.Label(self.setup, text = self.com)
        self.statusSpaceContain = tk.Frame(self.frame)
        self.statusSpace = tk.LabelFrame(self.frame, width = 200, height = 250)
        self.currentStatus = tk.Label(self.statusSpace, text = "", width = 25)
        self.progressBar = ttk.Progressbar(self.statusSpace, mode = 'determinate', length = 125)
    ### Loads objects into correct places
    def packObjects(self):

        self.out.pack()

        self.station_label.pack()

        self.setup.pack()
        self.statusSpace.pack()
        self.currentStatus.pack()
        self.progressBar.pack(pady = 5)
        self.frame.pack(side = tk.LEFT, padx = 10, fill = tk.Y)


    def addSubTitle(self, text_, color = HEADER):
        self.currentStatus.configure(text = text_, fg = color)
        self.addSeperator(self.statusSpace)
        addLabelToFrame(self.statusSpace, text_, color)

    def addSeperator(self, space):
        ttk.Separator(space).pack(fill = "x", expand = True)


    def process(self):
        self.restartProgressBar()

        start = time.time()
        changeServer = 1
        webtest = 1
        serailTunnel = 1
        ethernetTunnel = 1
        loadWebpage = 1
        loadFirmware = 1
        reset = 1

        self.fail = {
            "start" : 0,
            "changeServer" : 0,
            "webtest" : 0,
            "serialTunnel" : 0,
            "ethernetTunnel" : 0,
            "loadWebpage" : 0,
            "loadFirmware" : 0,
            "reset" : 0,
            "exit" : 0
        }

        # Get initial variables and options
        self.addSubTitle("Bootup Stage")
        addLabelToFrame(self.statusSpace, "Cycle power to the NET232Plus", INTERMEDIATE)
        self.fail["start"] = self.startConfig()

        currentMode = "friendly"

        if changeServer and self.calculateFail() == 0:
            # Make server changes
            self.addSubTitle("Server configuration stage")
            ip_str = '172.20.206.80'
            self.fail["changeServer"] = self.changeServer(ip_str, self.ser, currentMode)

        if self.calculateFail() == 0:
            # Exit config mode
            self.addSubTitle("Exit Stage")
            self.fail["exit"] = self.exitConfig(self.ser, currentMode)

        if webtest and self.calculateFail() == 0:
            self.addSubTitle("Web test stage")
            # Web test
            self.fail["webtest"] = self.performWebTest()

        if serailTunnel and self.calculateFail() == 0:
            self.addSubTitle("Serial ----> Ethernet test")
            self.serialToNetTest(port = "10001")

        if ethernetTunnel and self.calculateFail() == 0:
            self.addSubTitle("Ethernet ----> Serial Test")
            self.netToSerialTest(port = "10001")

        if loadWebpage and self.calculateFail() == 0:
            self.addSubTitle("Webpage Load")
            self.fail["loadWebpage"] = self.loadWeb()

        if loadFirmware and self.calculateFail() == 0:
            self.addSubTitle("Firmware Load")
            self.fail["loadFirmware"] = self.loadFirmware()

        currentMode = "friendly"
        if reset and self.calculateFail() == 0:
            self.addSubTitle("Reset module stage")
            reset_ip = '0.0.0.0'
            self.fail["reset"] = self.resetModule(currentMode)

        if self.calculateFail() == 0:
            # Exit config mode
            self.addSubTitle("Exit Stage")
            self.fail["exit"] = self.exitConfig(self.tn, currentMode)


        self.addSeperator(self.statusSpace)
        self.addSeperator(self.statusSpace)
        addLabelToFrame(self.statusSpace, "Finished program in " + str(round((time.time() - start), 2)) + " seconds", STATUSBLUE)

        ### Determine ending status
        sumFail = self.calculateFail()
        self.stopProgressBar(sumFail)
        if not sumFail:
            self.currentStatus.configure(text = "SUCCESS", fg = "#000000")
        else:
            self.currentStatus.configure(text = "FAIL", fg = "#000000")

    def calculateFail(self):
        sumFail = 0
        for key, value in self.fail.items():
            sumFail += value
        return sumFail
    ### Stops and configures progress bar to correct style
    def stopProgressBar(self, fail):
        self.progressBar.stop()
        if not fail:
            self.progressBar.configure(value = 100, style = "green.Horizontal.TProgressbar")
        else:
            self.progressBar.configure(value = 100, style = "red.Horizontal.TProgressbar")

    ### Restarts thread with new instantiation
    def createNewThread(self):
        self.thread = threading.Thread(target = self.process)
        self.thread.start()

    ### Resets styles and progress of progress bar
    def restartProgressBar(self):
        self.progressBar.configure(value = 0, style = "Horizontal.TProgressbar")
        self.progressBar.start()

    def startConfig(self):
        startup = waitForResponse(self.ser, 15, "x")
        fail = exitOnResponse(startup, timeoutMessage, self.statusSpace)
        # Response should be self startup screen
        if not fail:
            lines = startup.split("\n")
            for line in lines:
                if "MAC address" in line:
                    self.mac = line.split("MAC address ")[1];
                if "Press Enter" in line:
                    self.ser.write("\n\r".encode());
                    addLabelToFrame(self.statusSpace, self.mac + " entering config mode")

            self.getIPA(1)
        return fail

    def makeChoice(self, choice, port):
        print("(Debug) Choice: " + str(choice))
        port.write((str(choice) + "\n").encode())

    def exitConfig(self, port, mode):
        if mode == "friendly":
            choice = 9
            exitChoice = "Parameters stored"
        elif mode == "setup":
            choice = "G0"
            exitChoice = ""
        self.makeChoice(choice, port)
        close = waitForResponse(port, 3)
        print(close)
        if mode == "setup":
            self.makeChoice("QU", port)
            # print(waitForResponse(port, 3))
        if exitChoice in close:
            addLabelToFrame(self.statusSpace, "Exiting config mode...")
            port.close()

        return 0


    def changeServer(self, ip_str, port, mode):
        try:
            ipaddress.ip_address(ip_str)
        except ValueError:
            addLabelToFrame(self.statusSpace, "IP Address formatted incorrectly...Exiting", FAILRED)
            self.exitConfig(self.ser)
            return 1
        self.ipa = ip_str
        addLabelToFrame(self.statusSpace, "New IP Addr: " + self.ipa)
        ipArr = self.ipa.split(".")

        if mode == "friendly":
            # This uses the human interface mode
            self.makeChoice(0, port)
            for i in range(0,4):
                self.makeChoice(ipArr[i], port)
                waitForResponse(port, .5)
            response = ""
            while "Your choice" not in response:
                self.makeChoice("\r", port) # Just press enter, aka don't change settings
                response = waitForResponse(port, .5)

        elif mode == "setup":
            setup0 = []
            self.makeChoice("G0", port)
            response = ""
            while "0>" not in response:
                response = waitForResponse(port, 1, until = "\r\n")
                if response[0] == ":": # only parts of the setup record
                    setup0.append(response)
            ipIndex = 9
            for part in ipArr:
                newPart = hex(int(part))[-2:].upper().replace("X", "0")
                setup0[0] = setup0[0][:ipIndex] + newPart + setup0[0][ipIndex+2:]
                ipIndex += 2
            self.makeChoice("S0", port)
            str = ""
            for part in setup0:
                str += part
            # self.makeChoice(str, port)
            self.tn.write(str.encode())
            print(waitForResponse(port, until = "0>"))
        return 0

    def getIPA(self, initial):
        if not initial:
            self.ser.write("\r".encode())
        instructions = waitForResponse(self.ser, 5)
        exitOnResponse(instructions, timeoutMessage, self.statusSpace)
        sections = instructions.split("***")
        for section in sections:
            if "IP addr " in section:
                ipaStart = section.split("IP addr ")[1]
                potential = ipaStart.split(",")[0]
                try:

                    ipaddress.ip_address(potential)
                    self.ipa = potential
                    addLabelToFrame(self.statusSpace, "IP addr: " + self.ipa)
                except:
                    pass

    def openConfigWebpage(self):
        webbrowser.open("http://" + self.ipa)

    def performWebTest(self):
        url = "http://" + self.ipa
        addLabelToFrame(self.statusSpace, "Pinging " + url)
        try:
            urllib.request.urlopen(url).read()
            # addLabelToFrame(self.statusSpace, "Successful GET request", OKGREEN)
            addLabelToFrame(self.statusSpace, "Web manager set up", OKGREEN)
            return 0
        except:
            addLabelToFrame(self.statusSpace, "Failed GET request...Exiting")
            return 1

    def serialToNetTest(self, port):
        numComs = 100

        self.ser.open()
        HOST = self.ipa
        addLabelToFrame(self.statusSpace, "Establishing connection to " + HOST + " @ port " + port)
        self.tn = telnetlib.Telnet(HOST, port)

        # addLabelToFrame(self.statusSpace, "Writing data to serial")
        for i in range(0, numComs):
            self.ser.write("test".encode())
        self.ser.write("exit".encode())

        # addLabelToFrame(self.statusSpace, "Reading data from ethernet")
        response = self.tn.read_until("exit".encode()).decode()

        self.tn.close()
        self.ser.close()

        if response.count("test") == numComs:
            addLabelToFrame(self.statusSpace, "Successful Serial ----> Ethernet test", OKGREEN)
            return 0
        else:
            addLabelToFrame(self.statusSpace, "Failed Serial ----> Ethernet test", FAILRED)
            return 1


    def netToSerialTest(self, port):
        numComs = 100

        self.ser.open()
        HOST = self.ipa
        addLabelToFrame(self.statusSpace, "Establishing connection to " + HOST + " @ port " + port)
        self.tn = telnetlib.Telnet(HOST, port)

        # addLabelToFrame(self.statusSpace, "Writing datat to ethernet")
        for i in range(0, numComs):
            self.tn.write("test".encode())
        self.tn.write("exit".encode())

        # addLabelToFrame(self.statusSpace, "Reading data from serial")
        response = readSerialWord(self.ser)

        self.tn.close()
        self.ser.close()

        if response.count("test") == numComs:
            addLabelToFrame(self.statusSpace, "Successful Ethernet ----> Serial test", OKGREEN)
            return 0
        else:
            addLabelToFrame(self.statusSpace, "Failed Ethernet ----> Serial test", FAILRED)
            return 1

    def resetModule(self, mode):
        HOST = self.ipa
        port = "9999"
        self.tn = telnetlib.Telnet(HOST, port)
        response = self.tn.read_until("Mode".encode()).decode()
        if mode == "setup":
            self.tn.write("M\n".encode())
            next = self.tn.read_until("0>".encode(), 5).decode()
        elif mode == "friendly":
            self.tn.write("\n\r".encode())
            next = self.tn.read_until("Your choice ?".encode(), 5).decode()
        reset_ip = '0.0.0.0'
        self.changeServer(reset_ip, self.tn, mode)
        return 0

    def load(self, ip, file, location):
        pass

    def loadWeb(self):
        pass
        addLabelToFrame(self.statusSpace, "Loading .cob file")
        return 0

    def loadFirmware(self):
        pass
        addLabelToFrame(self.statusSpace, "Loading .rom file")
        return 0

### Read COM ports from config file and returned organized lists of ports
def getCOMPorts():
    devices = []
    port_file = 1
    if len(sys.argv) == 2:
        port_file = sys.argv[1]
    with open('cfg.txt', 'r+', encoding='utf-8' ) as mp:
        mp.readline() #first line is instructions
        for line in mp.readlines():
            if "COM" in line:
                devices.append(line.split("\n")[0])
        return devices

### Reads counter file and returns value in the file
def getNumDevicesLoaded():
    try:
        with open("device_counter.txt", 'r+', encoding = 'utf-8') as dev:
            ret = int(dev.readline())
            dev.close()
            return ret
    except IOError:
        with open("device_counter.txt", "w", encoding = 'utf-8') as file:
            file.write('0')
            file.close()
            return 0

### Reconfigures parameter label to append input text
def addTextToLabel(label, textToAdd):
    label.configure(text = label.cget("text") + textToAdd);

def addLabelToFrame(frame, textToAdd, color = "#000000"):
    add = tk.Label(frame, text = textToAdd, fg = color)
    add.pack(pady = 0)


### Resets device counter
def clearDevCounter():
    with open("device_counter.txt", 'w+', encoding = 'utf-8') as dev:
        dev.write('0')
        dev.close()
    loaded.set(0)

### Callback for updating IntVar variable represeting successful device programmings
def updateDevicesLoaded(*args):
    devicesLoaded.configure(text = ("Devices Loaded: " + str(loaded.get())).ljust(long_len))
    with open("device_counter.txt", 'w+', encoding = 'utf-8') as dev:
        dev.write(str(loaded.get()))
        dev.close()

class Application:
    def __init__(self, parent):
        global loaded, devicesLoaded
        loaded = IntVar()
        loaded.set(getNumDevicesLoaded())
        loaded.trace("w", updateDevicesLoaded)
        s = ttk.Style()
        s.theme_use('default')
        s.configure("red.Horizontal.TProgressbar", foreground='red', background='red')
        s.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
        self.parent = parent
        self.parent.title("NET232Plus Programmer")
        self.stations = []
        self.frame = tk.Frame(self.parent)
        # self.configureMenu()
        self.titleLabel = tk.Label(self.frame, text = 'Details/Instructions', font = 10)
        self.instructions = tk.Label(self.frame, text = '- Programming stations \
are labelled with both COM ports listed in config.txt\n \
            - Click START to begin the upload and verification', pady = 5)
        devices = getCOMPorts()
        # Size of window based on how many stations are present
        root_width = max(700, (len(devices) - 1) * 205)
        self.parent.geometry(str(root_width) + "x900+0+0")
        long_len = 10
        devicesLoaded = tk.Label(self.frame, text = ("Devices Loaded: " + str(loaded.get())).ljust(long_len), pady = 10)
        self.buttonFrame = tk.Frame(self.frame)
        self.clearCounter = tk.Button(self.buttonFrame, text = "Clear Counter", width = 10, bg = gridColor, height = 2, command = clearDevCounter)
        self.start = tk.Button(self.buttonFrame, text = "START", width = 22, bg = gridColor, height = 3, command = self.startUpload)
        self.packObjects()
        for device in devices:
            self.stations.append(Station(root, device))

    ### Places objects on screen in correct format
    def packObjects(self):
        self.frame.pack(side = tk.TOP)
        # self.titleLabel.pack()
        # self.instructions.pack()
        self.clearCounter.pack(pady = 5, side = tk.LEFT, padx = 15)
        self.start.pack(side = tk.LEFT, pady = 5)
        self.buttonFrame.pack(side = tk.LEFT, padx = 20)
        devicesLoaded.pack(side = tk.RIGHT)


    ### Create and "pack" menu for main root window
    def configureMenu(self):
        menubar = tk.Menu(self.parent)

        filemenu = tk.Menu(menubar, tearoff = 0)
        filemenu.add_command(label = "Open")
        filemenu.add_command(label = "Print")

        editmenu = tk.Menu(menubar, tearoff = 0)
        editmenu.add_command(label = "Undo")
        editmenu.add_command(label = "Redo")

        menubar.add_cascade(label = "File", menu = filemenu)
        menubar.add_cascade(label = "Edit", menu = editmenu)
        self.parent.configure(menu = menubar)

    ### Trigger function for START button which begins/continues each Station thread
    def startUpload(self):
        #loaded.set(getNumDevicesLoaded())
        for stat in self.stations:
            children = stat.statusSpace.winfo_children()
            for i in range(2, len(children)):
                children[i].destroy()
            if not stat.thread.is_alive():
                stat.createNewThread()
                if stat.ser.isOpen() == False:
                    stat.ser.open()

### Instantiate the root window and start the Application
if __name__ == "__main__":
    root = tk.Tk()
    a1 = Application(root)
    root.mainloop()

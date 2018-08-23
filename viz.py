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

class Device:
    def __init__(self, web_files_, firmware_files_):
        self.web_files = web_files_
        self.firmware_files = firmware_files_

deviceOptions = {
    "NET232Plus" : Device(firmware_files_ = dict(X6 = r"files/NET232pl_6807GC.rom"), web_files_ = dict(WEB1 = r"files\NET232pl_webm_1902.cob")),
    "NET232PlusRecover" : Device(firmware_files_ = dict(X6 = r"files/Recover/xpico_61001.rom"), web_files_ = dict(WEB1 = r"files/Recover/xpico_webm_2006.cob"))
}

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
    def __init__(self, parent_, com_, stat_num):
        self.com = com_
        try:
            self.ser = serial.Serial(self.com, baudrate = 9600, timeout = .1)
        except serial.SerialException as e:
            messagebox.showinfo("Serial Error", "Cannot open " + self.com + "\nPlease kill and restart the program")
            exit(1);
        self.mac = self.ipa = ""
        self.programIPA = "172.20.206.8" + str(stat_num)
        self.thread = threading.Thread(target = self.process)
        self.frame = tk.Frame(parent_)
        self.initComponents()
        self.packObjects()

    class Step:
        def __init__(self, name_, signal_, func_, fail_, args_):
            self.name = name_
            self.signal = signal_
            self.func = func_
            self.fail = fail_
            self.args = args_

        def execute(self):
            self.fail = self.func(*self.args)

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

        ### Change the settings to perform certain actions here
        changeServer = 1
        webtest = 1
        serialTunnel = 1
        ethernetTunnel = 1
        loadWebpage = 1
        loadFirmware = 1
        reset = 1
        log = 1


        currentMode = "friendly"
        self.steps = []

        self.order = {
            "Bootup Stage" : [1, self.startConfig, 0, []],
            "Server Configuration Stage" : [changeServer, self.changeServer, 0, [self.programIPA, "serial", currentMode]],
            "Exit Stage" : [1, self.exitConfig, 0, ["serial", currentMode]],
            "Web test Stage" : [webtest, self.performWebTest, 0, []],
            "Serial ----> Ethernet test" : [serialTunnel, self.serialToNetTest, 0, ["10001"]],
            "Ethernet ----> Serial test" : [ethernetTunnel, self.netToSerialTest, 0, ["10001"]],
            "Webpage Load" : [loadWebpage, self.load, 0, ["web"]],
            "Firmware Load" : [loadFirmware, self.load, 0, ["firmware"]],
            "Reset Stage" : [reset, self.resetModule, 0, [currentMode]],
            "Exit Stage*" : [reset, self.exitConfig, 0, ["telnet", currentMode]],
            "Logging Stage" : [log, self.logRun, 0, []]
        }

        for key, value in self.order.items():
            indv = Station.Step(key, value[0], value[1], value[2], value[3])
            self.steps.append(indv)

        for step in self.steps:
            if step.signal and self.calculateFail() == 0:
                self.addSubTitle(step.name)
                step.execute()

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
        for step in self.steps:
            sumFail += step.fail
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
        addLabelToFrame(self.statusSpace, "Cycle power to the device", INTERMEDIATE)
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
        port.write((str(choice) + "\n").encode())

    def exitConfig(self, port, mode):
        port = self.getPortFromKeyWord(port)
        if mode == "friendly":
            choice = 9
            exitChoice = "Parameters stored"
        elif mode == "setup":
            choice = "G0"
            exitChoice = ""
        self.makeChoice(choice, port)
        close = ""
        startTime = time.time()
        while exitChoice not in close and time.time() - startTime < 5:
            close = waitForResponse(port, 1)
        addLabelToFrame(self.statusSpace, "Exiting config mode...")
        port.close()
        if exitChoice in close:
            return 0
        else:
            return 1


    def changeServer(self, ip_str, port, mode):
        port = self.getPortFromKeyWord(port)
        try:
            ipaddress.ip_address(ip_str)
        except ValueError:
            addLabelToFrame(self.statusSpace, "IP Address formatted incorrectly...Exiting", FAILRED)
            self.exitConfig(port)
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
        self.changeServer(reset_ip, "telnet", mode)
        return 0

    def load(self, type):
        device = deviceOptions[deviceChosen.get()]
        if type == "web":
            dict = device.web_files
        elif type == "firmware":
            dict = device.firmware_files
        addLabelToFrame(self.statusSpace, "Opening a shell to load " + type + " files")
        totalFileTransferErrors = 0
        for location, file in dict.items():
            tftpCommand = "loadFile.sh " + self.ipa + " " + file + " " + location + " " + type
            totalFileTransferErrors += subprocess.call(tftpCommand, shell = True)
        return totalFileTransferErrors

    def logRun(self):
        full_date = str(datetime.datetime.now())
        log_str = "|" + full_date + " " + self.mac + " " + deviceChosen.get().ljust(19) + " "
        if not self.calculateFail():
            log_str += "SUCCESS |\n"
        else:
            log_str += "  FAIL  |\n"
        log_filename = "log.txt"
        with open(log_filename, 'a+',encoding='utf-8') as log:
            log.write(log_str)
            log.close()

    def getPortFromKeyWord(self, keyword):
        if keyword == "serial":
            return self.ser
        elif keyword == "telnet":
            return self.tn

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
        global loaded, devicesLoaded, deviceChosen
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

        OPTIONS = []
        for option in deviceOptions:
            OPTIONS.append(option)
        # print(OPTIONS)

        def callback(*args):
            device_details = deviceOptions[deviceChosen.get()]
            # print(device_details.web_files)
            # print(device_details.firmware_files)

        deviceChosen = StringVar(self.parent)
        deviceChosen.set(OPTIONS[0]) # default value
        deviceChosen.trace("w", callback)
        self.optionMenu = tk.OptionMenu(self.frame, deviceChosen, *OPTIONS)

        self.packObjects()
        for d in range(0, len(devices)):
            self.stations.append(Station(root, devices[d], d))

    ### Places objects on screen in correct format
    def packObjects(self):
        self.frame.pack(side = tk.TOP)
        # self.titleLabel.pack()
        # self.instructions.pack()
        self.clearCounter.pack(pady = 5, side = tk.LEFT, padx = 15)
        self.start.pack(side = tk.LEFT, pady = 5)
        self.buttonFrame.pack(side = tk.LEFT, padx = 20)
        devicesLoaded.pack(side = tk.RIGHT)
        self.optionMenu.pack(side = tk.RIGHT, padx = 20)


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

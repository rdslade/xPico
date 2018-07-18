### Test serial connections to xPico
import serial
import time
import ipaddress
import webbrowser
import urllib.request
import telnetlib

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

timeoutMessage = bcolors.fail_str("TIMED OUT WAITING FOR xPICO...EXITING")

### Helper function for reading serial words
def readSerialWord(ser_port):
    char = '0'
    response = ""
    # Continue reading word until not more chars
    while char != '':
        char = ser_port.read().decode()
        response += char
    return response

def waitForResponse(serPort, timeout = 10, input = ""):
    response = ""
    start = time.time()
    while response == "" and time.time() - start < timeout:
        if input != "":
            serPort.write(input.encode())
        response = readSerialWord(serPort)
    return response

def exitOnResponse(response, message, exitSeq = ""):
    if response == exitSeq:
        print(message)
        exit()

class Station:
    def __init__(self, com_):
        self.ser = serial.Serial(com_, baudrate = 9600, timeout = .1)
        self.mac = self.ipa = ""

    def startConfig(self):
        startup = waitForResponse(self.ser, 10, "x")
        exitOnResponse(startup, timeoutMessage)
        # Response should be xPico startup screen
        lines = startup.split("\n")
        for line in lines:
            if "MAC address" in line:
                self.mac = line.split("MAC address ")[1];
            if "Press Enter" in line:
                self.ser.write("\n\r".encode());
                print(self.mac + " entering config mode")
        self.getIPA(1)

    def makeChoice(self, choice):
        self.ser.write((str(choice) + "\n").encode())

    def exit(self):
        self.makeChoice(9)
        close = waitForResponse(self.ser, 3)
        if "Parameters stored" in close:
            print("Exiting config mode...")
            self.ser.close()

    def changeServer(self, ip_str):
        try:
            ipaddress.ip_address(ip_str)
        except ValueError:
            print(bcolors.fail_str("IP Address formatted incorrectly...Exiting"))
            self.exit()
            exit()
        self.ipa = ip_str
        print("New IP Addr: " + self.ipa)
        ipArr = self.ipa.split(".")
        self.makeChoice(0)
        for i in range(0,4):
            self.makeChoice(ipArr[i])
            waitForResponse(self.ser, 3)
        count = 0
        while count < 3:
            self.makeChoice("\r") # Just press enter, aka don't change settings
            waitForResponse(self.ser, 3)
            count += 1

    def getIPA(self, initial):
        if not initial:
            self.ser.write("\r".encode())
        instructions = waitForResponse(self.ser, 5)
        exitOnResponse(instructions, timeoutMessage)
        sections = instructions.split("***")
        for section in sections:
            if "IP addr " in section:
                ipaStart = section.split("IP addr ")[1]
                potential = ipaStart.split(",")[0]
                try:
                    ipaddress.ip_address(potential)
                    self.ipa = potential
                    print("IP addr: " + self.ipa)
                except:
                    pass

    def openConfigWebpage(self):
        print("Opening webpage")
        webbrowser.open("http://" + self.ipa)

    def performWebTest(self):
        url = "http://" + self.ipa
        print("Pinging " + url)
        try:
            urllib.request.urlopen(url).read()
            print(bcolors.success_str("Successful GET request"))
            print(bcolors.success_str("Web manager set up"))
        except:
            print(bcolors.fail_str("Failed GET request...Exiting"))
            exit()

    def serialToNetTest(self, port):
        numComs = 100

        self.ser.open()
        HOST = self.ipa
        print("Establishing connection to " + HOST + " @ port " + port)
        self.tn = telnetlib.Telnet(HOST, port)

        print("Writing data to serial")
        for i in range(0, numComs):
            self.ser.write("test".encode())
        self.ser.write("exit".encode())

        print("Reading data from ethernet")
        response = self.tn.read_until("exit".encode(), 10).decode()
        if response.count("test") == numComs:
            print(bcolors.success_str("Successful Serial ----> Ethernet test"))

        self.tn.close()
        self.ser.close()

    def netToSerialTest(self, port):
        numComs = 100

        self.ser.open()
        HOST = self.ipa
        print("Establishing connection to " + HOST + " @ port " + port)
        self.tn = telnetlib.Telnet(HOST, port)

        print("Writing data to ethernet")
        for i in range(0, numComs):
            self.tn.write("test".encode())
        self.tn.write("exit".encode())

        print("Reading data from serial")
        response = readSerialWord(self.ser)

        if response.count("test") == numComs:
            print(bcolors.success_str("Successful Ethernet ----> Serial test"))

        self.tn.close()
        self.ser.close()

    def loadWeb(self):
        print("Loading .cob file")


if __name__ == "__main__":
    start = time.time()
    changeServer = 1
    webtest = 1
    serailTunnel = 1
    ethernetTunnel = 1
    loadWebpage = 0

    # Init xPico
    xpico = Station("COM24")
    # Get initial variables and options
    print(bcolors.header_str("Bootup stage"))
    print(bcolors.intermediate_str("Cycle power to NET232Plus"))
    xpico.startConfig()

    if changeServer:
        # Make server changes
        print(bcolors.header_str("\nServer configuration stage"))
        ip_str = '172.20.206.81'
        xpico.changeServer(ip_str)
        #xpico.openConfigWebpage()

    # Exit config mode
    print(bcolors.header_str("\nExit stage"))
    xpico.exit()

    if webtest:
        print(bcolors.header_str("\nWeb test stage"))
        # Web test
        xpico.performWebTest()

    if serailTunnel:
        print(bcolors.header_str("\nSerial --> Ethernet test"))
        xpico.serialToNetTest(port = "10001")

    if ethernetTunnel:
        print(bcolors.header_str("\nEthernet --> Serial test"))
        xpico.netToSerialTest(port = "10001")

    if loadWebpage:
        print(bcolors.header_str("\nWebpage Load"))
        xpico.loadWeb()

    print(bcolors.underline_str("\nFinished program in " + str(round((time.time() - start), 2)) + " seconds"))

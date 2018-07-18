import serial

com = input("Enter the COM port: ")
xpicoSer = serial.Serial(com, baudrate = 9600, timeout = .1)
xpicoSer.write("9\n\r".encode())
print("Exited config mode")

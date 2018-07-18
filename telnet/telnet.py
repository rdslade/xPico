### Test telnet connections to xPico
import telnetlib
HOST = "172.20.200.106"
PORT = "9999"

tn = telnetlib.Telnet(HOST, PORT, 10)

response = tn.read_all()

print(response.decode())

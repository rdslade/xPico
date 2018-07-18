import tftpy

fileToUpload = r"C:\Users\Julia\Desktop\GridConnect\LabUpdate\xPico\files\NET232pl_webm_1902.cob"

client = tftpy.TftpClient('172.20.206.81', 69)
client.upload("WEB1", fileToUpload)
#client.download(r"c:\cobox\production\tftp", "test")
print("success")

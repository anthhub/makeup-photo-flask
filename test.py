import socket
hostname = socket.gethostname()
print(hostname)
ip = socket.gethostbyname(hostname)
print(ip)

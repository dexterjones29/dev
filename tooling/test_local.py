import os
import sys
import socket

print(f'Host: {socket.gethostname()}')
print(f'Python: {sys.executable}')
print(f'Working directory: {os.getcwd()}')
print(f'Home: {os.path.expanduser('~')}')
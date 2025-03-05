'''
This script is to be run on the PC (server) that will control all the traffic and the printers

(Expected to have good computational resources)
'''

import socket
import os
from tqdm import tqdm
from time import sleep
from colorama import Fore, Back, Style
from modules.subtle_defs_PC import *


# VARS -----------------------------------------------------------------------------------------------------------------------------------------------------

STORAGE_DIR = 'RCVD'
HOST_IP = socket.gethostbyname(socket.gethostname()) # HOST_IP = '127.0.0.1'
PORT = 7878
CONNECTION_LIMIT = SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
STATUS = None


# CONNECT -----------------------------------------------------------------------------------------------------------------------------------------------------

SERVER.bind((HOST_IP, PORT))
SERVER.listen(CONNECTION_LIMIT)
print(f'Listening for printers on: {HOST_IP}:{PORT}')

printer_socket, address = SERVER.accept()
print('Connected to:', address)


# INITIALISE -----------------------------------------------------------------------------------------------------------------------------------------------------

printer_info = printer_socket.recv(1024).decode('utf-8')
print('Connected Device Information:\n', printer_info)

printer_socket.send('OK'.encode('utf-8'))
if printer_socket.recv(1024).decode('utf-8') == 'RCVD:OK':
    STATUS = 'OK'
else:
    print('Could not initialise connection...')
    quit() # EXIT

print(Fore.GREEN + '\n\nINITIALISED!\n\n' + Style.RESET_ALL)



# FUNCTIONS -----------------------------------------------------------------------------------------------------------------------------------------------------

def exec_cmd(command: str):
    '''
    This function contains the decision tree of all the commands including passing it down to the printer.'''

    # Send command and get affirmation
    printer_socket.send(command.encode('utf-8'))
    if printer_socket.recv(1024).decode('utf-8') == f'RCVD:{command}':
        print('\t\t\t\t\t✅\n')
    else:
        print('❌ Not Sent')

    
    
    # Do the work - together

    
    if command == 'CLEAR':
        os.system('cls')  

    elif command == 'QUIT':
        printer_socket.close()
        print('Closing...')
        quit()

    elif command == 'SENDFILE':
        # GET FILE
        file_location = input(Fore.LIGHTWHITE_EX + 'File Location: ' + Style.RESET_ALL)


        # CHECK FILE
        file_location = file_location.replace('/', '\\')

        if ';' in file_location:
            print("Error! Filename can't have ';' in it...")
            printer_socket.send('ABORT'.encode('utf-8'))
            return
        
        if not os.path.exists(file_location):
            print(f'⚠️ {file_location} does not exist\n')
            printer_socket.send('ABORT'.encode('utf-8'))
            return

        filesize = os.path.getsize(file_location)
        FILENAME = file_location[file_location.rfind('\\')+1:]

        if '.gcode' not in FILENAME:
            print(f'⚠️ File is not a .gcode\n')
            printer_socket.send('ABORT'.encode('utf-8'))
            return


        # Send File details
        printer_socket.send(f'SENDFILE:{FILENAME};{filesize}'.encode('utf-8')) # Send details
        RESPONSE = printer_socket.recv(1024).decode('utf-8')
        if RESPONSE != 'RTR':
            print(RESPONSE)
            return
        
        
        # RTR - Start sending the filestream


        with open(file_location, "rb") as file:
            print('Starting File Transfer...')

            progress = tqdm(total=filesize) # Initialise
            while True:
                bytes_read = file.read(1024)
                
                if not bytes_read:
                    # file transmitting is done
                    break
                printer_socket.sendall(bytes_read)
                progress.update(len(bytes_read))
            progress.close()

        print(f"'{file_location}' sent!")

    elif command == 'START_PRINTJOB':
        menu = printer_socket.recv(1024).decode('utf-8')
        print(menu)
        index = input('Choose file to print: ')

        printer_socket.send(index.encode('utf-8'))

        ok = printer_socket.recv(1024).decode('utf-8')
        print(ok)
        if ok != 'OK':
            return

        # PRINT JOB IS STARTING
        total_lines = int(printer_socket.recv(1024).decode('utf-8').replace('Total_Lines:', ''))
        print(f'PRINT JOB IS STARTING... {total_lines} lines')

        # Wait for print to get over...
        p_status = printer_socket.recv(1024).decode('utf-8')
        if p_status == 'PRINTED':
            print('✅ Printed ')

        
    elif command == 'GET_TEMPS':
        temps = printer_socket.recv(1024).decode('utf-8')
        temps = temps[temps.index('T:'):]
        print(temps)


# EVENT LOOP -----------------------------------------------------------------------------------------------------------------------------------------------------

while True:
    command = input(Fore.YELLOW + '>>> ' + Style.RESET_ALL)
    if command.strip() == '':
        continue

    exec_cmd(command.upper())


printer_socket.close()
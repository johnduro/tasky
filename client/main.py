#!/usr/bin/python

import readline, re, socket
# import the whole file
# import confirmation
# import class scolor from color.py
from scolors import Scolors
from exit import query_yes_no, exiting, exit_query
#Gestion Erreur Connection
import errno
from socket import error as socket_error
#gestion daemon
from daemon import Daemon

UNIX_SOCKET_PATH = "/tmp/taskmaster_unix_socket"

progs = {}

#liste des instructions considerees valides
valid = ["start ", "stop ", "restart ", "shutdown", "reload", "launch", "list", "info ", "info", "start_all", "stop_all"]
validQuery = ""
for instruc in valid:
    if (len(validQuery)):
        validQuery += "|"
    else:
        validQuery = "^"
    validQuery = validQuery + "(" + instruc + ")"
print Scolors.CYAN + "Type 'help' for commands." + Scolors.ENDC

def init_conn(clientsocket):
    try:
        # clientsocket.connect(('localhost', 8965))
        clientsocket.connect(UNIX_SOCKET_PATH)
        # clientsocket.connect("/tmp/conn")
    except socket_error as serr:
        # if serr.errno != errno.ECONNREFUSED:
            # Not the error we are looking for, re-raise
            # raise serr
        print Scolors.RED + "Can't connect to server." + Scolors.ENDC
        exiting()
    return clientsocket

def send_instruct(msg):
    """Envoi une instruction via les socket en localhost:8965"""
    clientsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    #now connect to the web server on port 80
    # - the normal http port
    clientsocket = init_conn(clientsocket)
    clientsocket.send(msg) #envoie instruction
    buf = clientsocket.recv(8)#recup length de la future reception
    if buf.isdigit():
        if(int(buf)):
            clientsocket.send("OK") #envoie instruction
            buf = clientsocket.recv(int(buf))
        if len(buf) > 0:
            print buf
    else:
        print "ERROR SERVER"

def help_instruction():
    print "Liste des instructions valides :\n" + str(valid)

def check_instruction(instruction):
    """check si l'instruction entree est valide"""
    if (not instruction):
        return 0
    elif (re.match("exit", instruction)):
        exit_query()
    elif (re.match("help", instruction)):
        help_instruction()
    elif (re.match(validQuery, instruction)):
        send_instruct(instruction)
    else:
        print Scolors.RED + "Not a valid instruction, type 'help' to get the list." + Scolors.ENDC
    return 0

def main():
    # daemon = MyDaemon('../server/')


    try:
        prompt = Scolors.BLUE + "TaskY~> " + Scolors.ENDC
        instruction = raw_input(prompt)
        while (42):
            if (check_instruction(instruction)):
                print instruction + ": " + Scolors.RED + "invalid command" + Scolors.ENDC
            instruction = raw_input(prompt)
    except KeyboardInterrupt:
        exiting()

main()
# for elem in p:
#   try:
#       e = psutil.Process(elem)
#       print elem, e.get_cpu_percent(interval=1)
#   except:
#       print elem, "no rights"

# print p


# datetime.datetime.fromtimestamp(p.create_time).strftime("%Y-%m-%d %H:%M:%S")

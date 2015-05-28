import yaml
import argparse
import subprocess
import sys
import psutil
import datetime
import time
import os, os.path #path pour remove de tmp
import readline, re, socket

from exit import exiting, Scolors
from subprocess import call
#SIMILI MACROS
UNIX_SOCKET_PATH = "/tmp/conn"

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf, args ):
        self.conf = conf
        self.args = args
        self.initConn()

    def initConn( self ):
        self.serversocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        #bind the socket to a public host,

        # UNIQUEMENT SOCKET AF_INET
        # self.serversocket.bind(('localhost', 8965))

        # UNIQUEMENT SOCKET AF_UNIX
        if os.path.exists( UNIX_SOCKET_PATH ):
            os.remove( UNIX_SOCKET_PATH ) # pour eviter que le dossier soit utilise on l efface.
        self.serversocket.bind(UNIX_SOCKET_PATH)

        #become a server socket
        self.serversocket.listen(5)

    def runTM( self ):
        self.initFirstLaunch()
        self.makeLoop()

    def makeLoop( self ):
        try:
            while (42):
                (self.clientsocket, address) = self.serversocket.accept()
                buf = self.clientsocket.recv(2048)
                if not 'programs' in self.conf:
                    raise NameError("No 'programs' in configuration")
                elif len(buf) > 0:
                    print buf
                    ret = self.exec_instruct(buf)
                    self.clientsocket.send(str(len(ret)))
                    if (len(self.clientsocket.recv(8))):
                        self.clientsocket.send(ret)
                else:
                    self.managePrograms(self.conf['programs'])
        except KeyboardInterrupt:
            exiting()

    def exec_instruct( self, instruct ):
        if (re.match("list", instruct)):
            return self.list_prog()
        elif (re.match("shutdown", instruct)):
            return self.shutdown()
        elif (re.match("list", instruct)):
            return self.list_prog()
        elif (re.match("start_all", instruct)):
            return self.start_all()
        elif (re.match("start ", instruct)):
            return self.start(instruct[6:])
        elif (re.match("stop ", instruct)):
            return self.stop(instruct[5:])
        elif (re.match("info ", instruct)):
            return self.info(instruct[5:])
        return "Instruction doesn't exist\n"

    def list_prog( self ):
        out = ""
        for (key, value) in self.conf['programs'].items():
            out += key + ":"
            params = "\n"
            for (k, val) in value.items():
                params += "\t" + str(k) + "\t" + str(val) + "\n"
            out += params
        return out

    def shutdown( self ):
        ret = "Shutting down"
        self.clientsocket.send(str(len(ret)))
        if (len(self.clientsocket.recv(8))):
            self.clientsocket.send(ret)
        exiting()
        return ""

    def start_all( self ):
        out = "Fonction start_all incomplete"

        return out

    def start( self, name ):
        out = "Fonction start incomplete"

        return out

    def stop( self, name ):
        out = "Fonction stop incomplete"

        return out

    def info( self, name ):
        out = "Fonction info incomplete"

        return out

    def managePrograms( self, programs ):
        for (key, value) in programs.items():
            #print key #p
            for proX in value['proX']:
                returnValue = proX[1].poll()
                #print "POLL" #p
                #print returnValue #p
                #print proX[1].pid #p
                if returnValue != None:
                    if value['autorestart'] == 'always' or value['autorestart'] == 'unexpected':
                        if value['startretries'] > 0 and returnValue not in value['exitcodes'] or value['autorestart'] == 'always':
                            self.relaunchProg(key, value)
                            # proX.append((datetime, psutil.Popen(value['cmd'].split())))
                        else:
                            self.exitingProg(key, value, returnValue)
                    elif value['autorestart'] == 'never':
                        continue

    def initFirstLaunch( self ):
        """lance tous les programs contenus dans self.conf['programs']"""
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")
        else:
            for (key, value) in self.conf['programs'].items():
                value['proX'] = []
                if value['autostart'] == True:
                    self.launchProg(key, value)

    def exitingProg( self, progName, progConf, returnValue):
        """lance les processus de progName avec la configuration dans progConf"""
        if self.args.verbose:
            print "exiting " + progName + " pid : " + str(progConf['proX'][0][1].pid) + " with return code " + str(returnValue)
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])

        progConf['proX'] = []
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)

    def relaunchProg( self, progName, progConf):
        """lance les processus de progName avec la configuration dans progConf"""
        progConf['startretries'] -= 1
        if self.args.verbose:
            print "ReLaunching process : " + progName
            print "Remaining retries : " + str(progConf['startretries'])
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])
        progConf['proX'] = []
        progConf['proX'].append((datetime, psutil.Popen(progConf['cmd'].split())))
        if self.args.verbose:
            print "pid : " + str(progConf['proX'][0][1].pid)
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)


    def launchProg( self, progName, progConf):
        """lance les processus de progName avec la configuration dans progConf"""
        if self.args.verbose:
            print "Launching process : " + progName
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])
        progConf['proX'].append((datetime, psutil.Popen(progConf['cmd'].split())))
        if self.args.verbose:
            print "pid : " + str(progConf['proX'][0][1].pid)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)
import yaml
import argparse
import subprocess
import sys
import psutil
from datetime import datetime # a voir !
import time
import os, os.path #path pour remove de tmp
import readline, re, socket
import pickle
import select
import pprint

from exit import exiting, Scolors
from subprocess import call

#SIMILI MACROS
UNIX_SOCKET_PATH = "/tmp/taskmaster_unix_socket"

LAUNCHED = 0
RUNNING = 1
STOPPING = 2
EXITED = 3
FAILED = 4

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf ):
        self.conf = conf
        # self.args = args
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

    def runTaskMaster( self ):
        self.initFirstLaunch()
        self.makeLoop()

    def makeLoop( self ):
        read_list = [self.serversocket]
        try:
            while (42):
                readable, writable, errored = select.select(read_list, [], [], 1)
                for s in readable:
                    if s is self.serversocket:
                        self.clientsocket, address = self.serversocket.accept()
                        read_list.append(self.clientsocket)
                    else:
                        buf = s.recv(2048)
                        if not 'programs' in self.conf:
                            raise NameError("No 'programs' in configuration")
                        elif len(buf) > 0:
                            print buf
                            ret = self.execInstruct(buf)
                            self.clientsocket.send(str(len(ret)))
                            if (len(self.clientsocket.recv(8))):
                                self.clientsocket.send(ret)
                        else:
                            s.close()
                            read_list.remove(s)

                self.managePrograms(self.conf['programs'])

                for (key, prog) in self.conf['programs'].items():
                    if prog['process'].poll() != None: #salope
                        print key + " TERMINATED with ret code : "
                        print prog['process'].returncode #salope
                        print "\n"
                    else:
                        print key + " launched..."
                    # (stdoutdata, stderrdata) = prog['process'].communicate()
                    # print prog['process'].returncode, stdoutdata
                # (self.clientsocket, address) = self.serversocket.accept()
                # buf = self.clientsocket.recv(2048)
                # else:
        except KeyboardInterrupt:
            exiting()

    def getConfig( self ):
        # print "NOOOOOO"
        sendConf = self.conf.copy()

        for (key, value) in sendConf['programs'].items():
            if "proX" in value:
                sendConf['programs'][key].pop("proX", None)

        serializedConf = pickle.dumps(sendConf)
        return serializedConf

    def execInstruct( self, instruct ):
        # print "YOLO"
        if (re.match("list", instruct)):
            return self.listProg()
        elif (re.match("shutdown", instruct)):
            return self.shutdown()
        elif (re.match("list", instruct)):
            return self.listProg()
        elif (re.match("start_all", instruct)):
            return self.startAll()
        elif (re.match("stop_all", instruct)):
            return self.stopAll()
        elif (re.match("start ", instruct)):
            return self.start(instruct[6:])
        elif (re.match("stop ", instruct)):
            return self.stop(instruct[5:])
        elif (re.match("restart ", instruct)):
            return self.start(instruct[8:])
        elif (re.match("info ", instruct)):
            return self.info(instruct[5:])
        elif (re.match("getConfig", instruct)):
            return self.getConfig()
        return "Instruction doesn't exist\n"

    def listProg( self ):
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

    def startAll( self ):
        out = ""
        for (key, value) in self.conf['programs'].items():
            out += self.launchProg(key, value) + "\n"

        return out

    def stopAll( self ):
        out = ""
        for (key, value) in self.conf['programs'].items():
            out += self.exitingProg(key, value) + "\n"

        return out

    def start( self, name ):
        out = self.launchProg(name, self.conf['programs'].get(name))
        return out

    def restart( self, name ):
        out = self.relaunchProg(name, self.conf['programs'].get(name))

        return out

    def stop( self, name ):
        out = self.exitingProg(name, self.conf['programs'].get(name))
        self.conf['programs'].get(name)['process'].terminate #salope
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
                            self.exitingProg(key, value)
                    elif value['autorestart'] == 'never':
                        continue

    def initFirstLaunch( self ):
        """lance tous les programs contenus dans self.conf['programs']"""
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")
        else:
            for (key, value) in self.conf['programs'].items():
                print "INIT FIRST LAUNCH : " + key + "< stap"
                value['proX'] = [] #salope
                value['processes'] = []
                if value['autostart'] == True:
                    self.launchProg(key, value)

    def exitingProg( self, progName, progConf):
        """lance les processus de progName avec la configuration dans progConf"""
        # if self.args.verbose:
        if self.conf["args"].verbose:
            print "exiting " + progName + " pid : " + str(progConf['proX'][0][1].pid) + " with return code " + str(returnValue)
        try :
            self.conf['programs'].get(progName)['process'].terminate() #salope
        except psutil.NoSuchProcess:
            print "Plus de process"
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
        out = "J'ai stoppe " + progName
        return out

    def relaunchProg( self, progName, progConf):
        """relance les processus de progName avec la configuration dans progConf"""
        progConf['startretries'] -= 1
        if self.conf["args"].verbose:
        # if self.args.verbose:
            print "ReLaunching process : " + progName
            print "Remaining retries : " + str(progConf['startretries'])
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])


        # MODIFIER BOUGER le POPEN dans launchProg
        progConf['proX'] = []
        progConf['proX'].append((datetime, psutil.Popen(progConf['cmd'].split())))


        if self.conf["args"].verbose:
        # if self.args.verbose:
            print "pid : " + str(progConf['proX'][0][1].pid)
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)

    def getEnv( self, progConf ):
        env = os.environ.copy()
        if 'env' in progConf.keys():
            for lines in progConf['env']:
                env[lines] = str(progConf['env'][lines])
        return env

    def getErrAndOut( self, progConf ):
        errRet = None
        outRet = None
        if "stderr" in progConf:
            errRet = open(progConf['stderr'], "a+")
        if "stdout" in progConf:
            outRet = open(progConf['stdout'], "a+")
        return (errRet, outRet)

    def getWorkingDir( self, progConf ):
        if 'workingdir' in progConf:
            workingDir = progConf['workingdir']
        else:
            workingDir = None
        return workingDir


    def launchProg( self, progName, progConf ):
        """lance les processus de progName avec la configuration dans progConf"""
        # REMETTRE !!!!!!!
        # if self.conf["args"].verbose:
        print "Launching process : " + progName # A SUPPRIMER

        verbose = "Launching process : " + progName + "\n"
        env = self.getEnv(progConf)
        (errProg, outProg) = self.getErrAndOut(progConf)
        workingDir = self.getWorkingDir(progConf)

        if 'umask' in progConf:
            print "UMSK FIRST"
            print "HERE " + str(progConf['umask'])
            # print int(progConf['umask'], 8)
            # oldMask = os.umask(int(progConf['umask'], 8))
            oldMask = os.umask(progConf['umask'])
            # oldMask = os.umask(0777 - progConf['umask'])

        for idx in range(progConf['numprocs']):
            print "NUMPROCS OF " + progName + " : " + str(idx)
            proc = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, cwd=workingDir)
            date = datetime
            progConf['processes'].append({'process' : (date, proc), 'status' : LAUNCHED})
            verbose += "pid : " + str(proc.pid) + date.strftime(", started at %H:%M:%S %a, %d %b %Y") + "\n"


        # p = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, cwd=workingDir)
        # self.conf['programs'].get(progName)['process'] = p #salope
        # progConf['proX'].append((datetime, p, LAUNCHED))
        # if self.conf["args"].verbose:
        # if self.args.verbose:
            # print "pid : " + str(progConf['proX'][0][1].pid)
        # ret = "Launching process : " + progName
        print verbose


        if 'umask' in progConf:
            print "UMSK SECOND"
            print "OLDMASK: " + str(oldMask)
            os.umask(oldMask)
            # os.umask(0777 - oldMask)


        outn = "Lancement du programme " + progName + " effectue..."
        return outn


#verifications a faire apres le parsing :
# verifier la presence de numprocs ou le mettre a 1
# verifier la presence de cmd sinon raise une exception


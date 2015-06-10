import yaml
import argparse
import subprocess
import sys
import psutil
import time
import os, os.path #path pour remove de tmp
import readline, re, socket
import pickle
import select
import pprint
import signal

from exit import exiting, Scolors
from subprocess import call
from datetime import datetime

#SIMILI MACROS
UNIX_SOCKET_PATH = "/tmp/taskmaster_unix_socket"

LAUNCHED = "LAUNCHED"
RUNNING = "RUNNING"
STOPPING = "STOPPING"
EXITED = "EXITED"
FAILED = "FAILED"

PROGRAM_NOT_FOUND = " : wrong program name, type 'list' to get all programs actually being monitored by Taskmaster\n"
# LAUNCHED = 0
# RUNNING = 1
# STOPPING = 2
# EXITED = 3
# FAILED = 4

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf ):
        self.conf = conf
        # self.args = args
        self.initConn()
        self.initLogFile()
        self.initSignals()

    def initSignals( self ):
        self.nameToSignals = {}
        for n in dir(signal):
            if n.startswith('SIG') and not n.startswith('SIG_'):
                self.nameToSignals[n] = getattr(signal, n)

    def initLogFile( self ):
        self.logFile = None
        if 'logfile' in self.conf:
            if 'enabled' in self.conf['logfile']:
                if self.conf['logfile']['enabled'] is True:
                    if 'path' in self.conf['logfile']:
                        self.logFile = open(self.conf['logfile']['path'], 'a+')
                    else:
                        self.logFile = open('taskmaster.log', 'a+')


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
        self.read_list = [self.serversocket]

    def runTaskMaster( self ):
        self.initFirstLaunch()
        self.makeLoop()

    def serverListen( self ):
        readable, writable, errored = select.select(self.read_list, [], [], 1)
        for s in readable:
            if s is self.serversocket:
                self.clientsocket, address = self.serversocket.accept()
                self.read_list.append(self.clientsocket)
            else:
                buf = s.recv(2048)
                if len(buf) > 0:
                    print buf #salope
                    ret = self.execInstruct(buf)
                    self.clientsocket.send(str(len(ret)))
                    if (len(self.clientsocket.recv(8))):
                        self.clientsocket.send(ret)
                    else:
                        s.close()
                        self.read_list.remove(s)

    def makeLoop( self ):
        try:
            while (42):
                if not 'programs' in self.conf:
                    raise NameError("No 'programs' in configuration")
                self.serverListen()
                # self.managePrograms(self.conf['programs'])
                self.managePrograms()
                # for (key, prog) in self.conf['programs'].items():
                #     if prog['process'].poll() != None: #salope
                #         print key + " TERMINATED with ret code : "
                #         print prog['process'].returncode #salope
                #         print "\n"
                #     else:
                #         print key + " launched..."
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
        # elif (re.match("list", instruct)):
        #     return self.listProg()
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

    def listProg( self ): #Liste les programmes et leur status, liste les PIDS des process (non ?) en meme temps et voila ##FAIT##
        # progConf['processes'].append({'process' : (date, proc), 'status' : LAUNCHED, 'retries' : 0, 'stoptime' : None})
        ret = str(len(self.conf['programs'])) + " programs being monitored :\n"
        for (key, value) in self.conf['programs'].items():
            failedProc = 0
            ret += "\t- " + key + " :\n"
            if 'processes' in value and len(value['processes']) > 0:
                for process in value['processes']:
                    if process['status'] is FAILED:
                        failedProc += 1
                        continue
                    ret += "\t\t " + process['status'] + "\t"
                    if (process['status'] is RUNNING or process['status'] is LAUNCHED):
                        ret += "pid " + str(process['process'][1].pid) + process['process'][0].strftime(", started at %H:%M:%S %a, %d %b %Y")
                    ret += "\n"
            if failedProc > 0:
                ret += "\t\t" + str(failedProc) + " failed process\n"
        if self.conf["args"].verbose:
            print ret
        return ret
            # verbose += "pid : " + str(proc.pid) + date.strftime(", started at %H:%M:%S %a, %d %b %Y") + "\n"
        # out = ""
        # for (key, value) in self.conf['programs'].items():
        #     out += key + ":"
        #     params = "\n"
        #     for (k, val) in value.items():
        #         params += "\t" + str(k) + "\t" + str(val) + "\n"
        #     out += params
        # return out

    def shutdown( self ): #Exit le serveur proprement apres avoir stoppe le reste
        ret = "Shutting down"
        self.clientsocket.send(str(len(ret)))
        if (len(self.clientsocket.recv(8))):
            self.clientsocket.send(ret)
        self.stopAll()
        print ret
        exiting()
        return "" #obligatoire ?

    # def launchProg( self, progName, progConf, nbRetries, nbProcess = None ):
    def startAll( self ): #Starte tous les programmes # A REFAIRE
        ret = "Starting all programs :\n"
        for (key, value) in self.conf['programs'].items():
            ret += self.startingProgram(key, value)
        return ret

        # out = ""
        # for (key, value) in self.conf['programs'].items():
        #     out += self.launchProg(key, value) + "\n"

        # return out

    def stopAll( self ):
        ret = "Stopping all programs :\n"
        for (key, value) in self.conf['programs'].items():
            ret += self.exitingProg(key, value)
        return ret

    def start( self, name ): # FAIT
        ret = ""
        if name in self.conf['programs']:
            ret += self.startingProgram(name, self.conf['programs'][name])
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret

    def restart( self, name ): # FAIT
        ret = ""
        if name in self.conf['programs']:
            ret += self.exitingProg(name, self.conf['programs'][name])
            ret += self.startingProgram(name, self.conf['programs'][name])
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret

    def stop( self, name ): #FAIT
        ret = ""
        if name in self.conf['programs']:
            ret += self.exitingProg(name, self.conf['programs'][name])
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret

    def info( self, name ):
        ret = ""
        if name in self.conf['programs']:
            progConf = self.conf['programs'][name]
            ret += name + " infos :\n"
            ret += "\tlaunching command: " + progConf['cmd'] + "\n"
            if 'workingdir' in progConf:
                "\tworking directory : " + progConf['workingdir'] + "\n"
            ret += "\tlogging files:\n"
            if 'stdout' in progConf or 'stdin' in progConf or 'stderr' in progConf:
                if 'stdout' in progConf:
                    ret += "\t\t- stdout : " + progConf['stdout'] + "\n"
                if 'stderr' in progConf:
                    ret += "\t\t- stderr : " + progConf['stderr'] + "\n"
                if 'stdin' in progConf:
                    ret += "\t\t- stdin : " + progConf['stdin'] + "\n"
            else:
                ret += "\t\t- no logging files\n"
            if 'env' in progConf and len(progConf['env']) > 0:
                ret += "\tenvironment variables :\n"
                for (key, value) in progConf['env'].items():
                    "\t\t- " + str(key) + " = " + str(value) + "\n"
            ret += "\tprocesses ("+ str(progConf['numprocs']) +" max process(es) running) :\n"
            # ret += "pid " + str(process['process'][1].pid) + process['process'][0].strftime(", started at %H:%M:%S %a, %d %b %Y")
            if 'processes' in progConf:
                for process in progConf['processes']:
                    ret += "\t\t- " + process['status'] + "\t"
                    if process['status'] is RUNNING or process['status'] is LAUNCHED:
                        ret += "pid " + str(process['process'][1].pid) + process['process'][0].strftime(", started at %H:%M:%S %a, %d %b %Y")
                    elif process['status'] is STOPPING or process['status'] is EXITED:
                        if process['stoptime'] is not None:
                            ret += process['stoptime'].strftime("stopped at %H:%M:%S %a, %d %b %Y")
                        else:
                            ret += process['process'][0].strftime(", started at %H:%M:%S %a, %d %b %Y")
                    elif process['status'] is FAILED:
                        ret += "exited with return code : " + str(process['process'][1].poll())
                        if process['stoptime'] is not None:
                            ret += process['stoptime'].strftime("stopped at %H:%M:%S %a, %d %b %Y")
                        else:
                            ret += process['process'][0].strftime(", started at %H:%M:%S %a, %d %b %Y")
                    ret += "\n"
            else:
                ret += "\t\t- no processes actually running\n"
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret
        # out = "Fonction info incomplete" #ON PRINT QUOI ?: infos detaille sur le prog : tous les processes plus certaines parties de la conf

        # return out

    # def managePrograms( self, programs ):
    def managePrograms( self ):
        for (key, value) in self.conf['programs'].items():
            # progConf['processes'].append({'process' : (date, proc), 'status' : LAUNCHED, 'retries' : 0, 'stoptime' : None})

            if 'processes' in value and len(value['processes']) > 0:
                for process in value['processes']:
                    if process['status'] is FAILED or process['status'] is EXITED:
                        continue
                    returnValue = process['process'][1].poll()
                    # PROCESS IS RUNNING
                    if returnValue is None:
                        dateNow = datetime.now()
                        if process['status'] is LAUNCHED:
                            dateDiff = (dateNow - process['process'][0]).total_seconds()
                            # print "DATEDIFF --> " + str(dateDiff)
                            if dateDiff > value['starttime']:
                                process['status'] = RUNNING
                        elif process['status'] is STOPPING:
                            # dateNow = datetime.now()
                            dateDiff = (dateNow - process['stoptime']).total_seconds()
                            if dateDiff > value['killtime']:
                                process['process'][1].send_signal(SIGKILL)
                                process['status'] = FAILED
                    # PROCESS IS NOT RUNNING
                    else:
                        if process['status'] is LAUNCHED:
                            self.relaunchProg(key, value, process)
                        if process['status'] is RUNNING:
                            if value['autorestart'] == 'always' or (value['autorestart'] == 'unexpected' and returnValue not in value['exitcodes']):
                                value['processes'].remove(process)
                                self.launchProg(key, value, value['startretries'], 1)
                            else:
                                if returnValue not in value['exitcodes']:
                                    process['status'] = FAILED
                                else:
                                    process['status'] = EXITED
                        if process['status'] is STOPPING:
                            process['status'] = EXITED


    def initFirstLaunch( self ):
        """lance tous les programs contenus dans self.conf['programs']"""
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")
        else:
            for (key, value) in self.conf['programs'].items():
                if value['autostart'] == True:
                    self.launchProg(key, value, value['startretries'])

    def exitingProg( self, progName, progConf):
        """quitte les processus de progName"""
        verbose = "Stopping process : " + progName + "\n"
        if 'processes' in progConf and len(progConf['processes']) > 0:
            for process in progConf['processes']:
                if process['process'][1].poll() is None:
                    verbose += "\t- process with pid " + str(process['process'][1].pid) + " is being sent SIG" + progConf['stopsignal'] + "\n"
                    process['process'][1].send_signal(self.nameToSignals["SIG" + progConf['stopsignal']])
                    process['status'] = STOPPING
                    process['stoptime'] = datetime.now()
        else:
            verbose += progName + " haven't been started, no processes to stop\n"

        if self.conf["args"].verbose:
            print verbose
        return verbose

        # if self.conf["args"].verbose:
        #     print "exiting " + progName + " pid : " + str(progConf['proX'][0][1].pid) + " with return code " + str(returnValue)
        # try :
        #     self.conf['programs'].get(progName)['process'].terminate() #salope
        # except psutil.NoSuchProcess:
        #     print "Plus de process"
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])

        # progConf['proX'] = []
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)
        # out = "J'ai stoppe " + progName
        # return out

    def relaunchProg( self, progName, progConf, process ):
        """relance les processus de progName avec la configuration dans progConf"""
        if process['retries'] > 0:
            verbose = "Program " + progName + " is being relaunched\n"
            if self.conf["args"].verbose:
                print verbose
            if self.logFile is not None:
                self.logFile.write(verbose)
            self.launchProg(progName, progConf, process['retries'] - 1, 1)
            progConf['processes'].remove(process)
        else:
            process['status'] = FAILED
            verbose = "Program " + progName + " has been relaunched too many times\n"
            if self.conf["args"].verbose:
                print verbose
            if self.logFile is not None:
                self.logFile.write(verbose)

    def getEnv( self, progConf ):
        env = os.environ.copy()
        if 'env' in progConf.keys():
            for lines in progConf['env']:
                env[lines] = str(progConf['env'][lines])
        return env

    def getInErrAndOut( self, progConf ):
        errRet = None
        outRet = None
        inRet = None
        if "stderr" in progConf:
            errRet = open(progConf['stderr'], "a+")
        if "stdout" in progConf:
            outRet = open(progConf['stdout'], "a+")
        if "stdin" in progConf:
            inRet = open(progConf['stdin'], "a+")
        return (errRet, outRet, inRet)

    def getWorkingDir( self, progConf ):
        if 'workingdir' in progConf:
            workingDir = progConf['workingdir']
        else:
            workingDir = None
        return workingDir

    def startingProgram( self, progName, progConf ):
        nbProcToRun = progConf['numprocs']
        if 'processes' in progConf:
            nbProcRunning = 0
            for process in progConf['processes']:
                if process['status'] is RUNNING or process['status'] is LAUNCHED:
                    nbProcRunning += 1
            nbProcToRun -= nbProcRunning
            if nbProcToRun <= 0:
                verbose = "Couldn't start " + progName + ", it's already running\n"
                if self.conf["args"].verbose:
                    print verbose
                return verbose
        verbose = self.launchProg(progName, progConf, progConf['startretries'], nbProcToRun)
        return verbose

    def launchProg( self, progName, progConf, nbRetries, nbProcess = None ):
        """lance les processus de progName avec la configuration dans progConf"""

        if 'processes' not in progConf:
            progConf['processes'] = []

        verbose = "Launching process : " + progName + "\n"
        env = self.getEnv(progConf)
        (errProg, outProg, inProg) = self.getInErrAndOut(progConf)
        workingDir = self.getWorkingDir(progConf)

        if 'umask' in progConf:
            oldMask = os.umask(progConf['umask'])

        for idx in range(progConf['numprocs']):
            if nbProcess != None:
                if idx >= nbProcess:
                    break
            print "NUMPROCS OF " + progName + " : " + str(idx)
            # proc = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, cwd=workingDir)
            proc = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, stdin=inProg, cwd=workingDir)

            date = datetime.now()
            progConf['processes'].append({'process' : (date, proc), 'status' : LAUNCHED, 'retries' : nbRetries, 'stoptime' : None})
            verbose += "pid : " + str(proc.pid) + date.strftime(", started at %H:%M:%S %a, %d %b %Y") + "\n"

        # p = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, cwd=workingDir)
        # self.conf['programs'].get(progName)['process'] = p #salope
        # progConf['proX'].append((datetime, p, LAUNCHED))
        # if self.conf["args"].verbose:
        # if self.args.verbose:
            # print "pid : " + str(progConf['proX'][0][1].pid)
        # ret = "Launching process : " + progName
        if self.conf["args"].verbose:
            print verbose

        if self.logFile is not None:
            self.logFile.write(verbose)

        if 'umask' in progConf:
            os.umask(oldMask)

        # outn = "Lancement du programme " + progName + " effectue..."
        return verbose


#verifications a faire apres le parsing :
# verifier la presence de numprocs ou le mettre a 1
# verifier la presence de cmd sinon raise une exception ERROR IMPORTANTE A REGLER
# verifier starttime ou le mettre a 0
# verifier stoptime ou le mettre a 0
# verifier startretries ou le mettre a 0
# verifier exitCodes
# rajouter une liste 'processes' dans les process au moment de la verification
# verifier les signaux mis dans le fichier de config
# verifier si il a un stopsignal sinon mettre sigterm ?
# verifier autorestart et raise si absent

# ajout message lors du stop d un programme stoppe
# probleme restart ?
# ajout timeout cote client quand il ne recoit pas de reponse du serv
# voir pour les retours, le \n de trop


# verifier les droits des fichiers de log

# verifier que toutes les actions (sauf liste etc..) sont logges

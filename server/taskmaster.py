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
import errno
from pprint import pprint

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

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf ):
        self.initSignals()
        self.conf = conf
        try:
            self.checkConf(self.conf)
        except NameError as e:
            print e.message
            exiting()
        self.initConn()
        self.initLogFile(self.conf)

    def checkConf( self, conf ):
        if not 'programs' in conf:
            raise NameError("Config : No 'programs' in configuration")
        if 'logfile' in conf and 'enabled' not in conf['logfile']:
            raise NameError("Config : No 'enabled' in logfile")
        for (key, value) in conf['programs'].items():
            if not 'cmd' in value:
                raise NameError("Config: No 'cmd' in program: " + key)
            if os.path.isfile(value['cmd'].split()[0]):
                value['cmd'] = os.path.abspath(value['cmd'])
            else:
                raise NameError("Command not found in absolute or relative path2 " + key)
            if not 'autorestart' in value:
                raise NameError("Config: No 'autorestart' in program: " + key)
            if not 'numprocs' in value or value['numprocs'] <= 0:
                value['numprocs'] = 1
            if not 'starttime' in value:
                value['starttime'] = 0
            if not 'killtime' in value:
                value['killtime'] = 0
            if not 'startretries' in value:
                value['startretries'] = 0
            if not 'exitcodes' in value:
                value['exitcodes'] = []
            if not 'stopsignal' in value:
                value['stopsignal'] = 'TERM'
            if 'SIG' + value['stopsignal'] not in self.nameToSignals:
                raise NameError("Config: Wrong signal for 'stopsignal' : " + value['stopsignal'])


    def reloadLogFile( self, newConf):
        if self.logFile is None and 'logfile' not in newConf:
            return
        elif self.logFile != None and 'logfile' not in newConf:
            self.logFile.close()
            self.logFile = None
        elif self.logFile is None and 'logfile' in newConf:
            self.initLogFile(newConf)
        elif self.logFile != None and 'logfile' in newConf:
            self.logFile.close()
            if 'enabled' in newConf['logfile'] and newConf['logfile']['enabled'] is True:
                self.initLogFile(newConf)

    def checkEnv( self, newEnv, oldEnv ):
        shared_items = set(newEnv.items()) & set(oldEnv.items())
        if len(shared_items) != len(oldEnv):
            return False
        return True

    def howManyProcessesRunning(self, processes):
        ret = 0
        for process in processes:
            if process['status'] == RUNNING or process['status'] == LAUNCHED:
                ret +=1
        return ret

    def reloadProcess( self, newConf ):
        oldPrograms = self.conf['programs']
        for (key, value) in newConf['programs'].items():
            if key not in oldPrograms and value['autostart'] is True:
                self.launchProg(key, value, value['startretries'])
            elif key in self.conf['programs']:
                if (value['cmd'] != oldPrograms[key]['cmd'] or
                    ('stdout' in value and 'stdout' not in oldPrograms[key]) or
                    ('stdout' not in value and 'stdout' in oldPrograms[key]) or
                    ('stdout' in value and 'stdout' in oldPrograms[key] and value['stdout'] != oldPrograms[key]['stdout']) or
                    ('stdin' in value and 'stdin' not in oldPrograms[key]) or
                    ('stdin' not in value and 'stdin' in oldPrograms[key]) or
                    ('stdin' in value and 'stdin' in oldPrograms[key] and value['stdin'] != oldPrograms[key]['stdin']) or
                    ('stderr' in value and 'stderr' not in oldPrograms[key]) or
                    ('stderr' not in value and 'stderr' in oldPrograms[key]) or
                    ('stderr' in value and 'stderr' in oldPrograms[key] and value['stderr'] != oldPrograms[key]['stderr']) or
                    ('workingdir' in value and 'workingdir' not in oldPrograms[key]) or
                    ('workingdir' not in value and 'workingdir' in oldPrograms[key]) or
                    ('workingdir' in value and 'workingdir' in oldPrograms[key] and value['workingdir'] != oldPrograms[key]['workingdir']) or
                    ('umask' in value and 'umask' not in oldPrograms[key]) or
                    ('umask' not in value and 'umask' in oldPrograms[key]) or
                    ('umask' in value and 'umask' in oldPrograms[key] and value['umask'] != oldPrograms[key]['umask']) or
                    ('env' in value and 'env' not in oldPrograms[key]) or
                    ('env' not in value and 'env' in oldPrograms[key]) or
                    ('env' in value and 'env' in oldPrograms[key] and self.checkEnv(value['env'], oldPrograms[key]['env']) != True)):
                    self.exitingProg(key, self.conf['programs'][key])
                    if self.howManyProcessesRunning( oldPrograms[key]['processes']) > 0:
                        self.launchProg(key, value, value['startretries'])
                elif value['numprocs'] != oldPrograms[key]['numprocs']:
                    value['processes'] = oldPrograms[key]['processes']
                    if value['numprocs'] > oldPrograms[key]['numprocs']:
                        self.launchProg(key, value, value['startretries'], (value['numprocs'] - oldPrograms[key]['numprocs']))
                    else:
                        self.exitingProg(key, value)
                        if self.howManyProcessesRunning( oldPrograms[key]['processes']) > 0:
                            self.launchProg(key, value, value['startretries'])
                else:
                    value['processes'] = oldPrograms[key]['processes']
        for (key, value) in oldPrograms.items():
            if key not in newConf['programs']:
                self.exitingProg(key, oldPrograms[key])

    def reloadConfig( self, signum, frame ):
        verbose = "Reloading configuration:\n"
        newConf = {}
        if 'configurationFiles' not in self.conf:
            raise NameError("Config error no file(s) for configuration")
        for _file in self.conf['configurationFiles']:
            try:
                openConf = yaml.load(open(_file, 'r'))
                verbose += "\treloading " + _file + '\n'
            except IOError:
                if errorConfig:
                    if self.logFile is not None:
                        self.logFile.write("Error opening configuration files while reloading\n")
            for (key, value) in openConf.items():
                if not key in newConf:
                    newConf[key] = value
                else:
                    newConf[key].update(value)
        newConf['configurationFiles'] = self.conf['configurationFiles']
        newConf['originalWD'] = self.conf['originalWD']
        newConf['args'] = self.conf['args']
        self.reloadLogFile(newConf)
        try:
            self.checkConf(newConf)
        except NameError as e:
            print e.message
            exiting()
        self.reloadProcess(newConf)
        self.conf = newConf
        if self.logFile is not None:
            self.logFile.write(verbose)
        if self.conf["args"].verbose:
            print verbose
        return verbose

    def initSignals( self ):
        self.nameToSignals = {}
        for n in dir(signal):
            if n.startswith('SIG') and not n.startswith('SIG_'):
                self.nameToSignals[n] = getattr(signal, n)
        signal.signal(signal.SIGHUP, self.reloadConfig)

    def initLogFile( self, conf ):
        self.logFile = None
        if 'logfile' in conf:
            if 'enabled' in conf['logfile']:
                if conf['logfile']['enabled'] is True:
                    if 'path' in conf['logfile']:
                        self.logFile = open(conf['logfile']['path'], 'a+')
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
        try:
            readable, writable, errored = select.select(self.read_list, [], [], 1)
            for s in readable:
                if s is self.serversocket:
                    self.clientsocket, address = self.serversocket.accept()
                    self.read_list.append(self.clientsocket)
                else:
                    buf = s.recv(2048)
                    if len(buf) > 0:
                        ret = self.execInstruct(buf)
                        self.clientsocket.send(str(len(ret)))
                        if (len(self.clientsocket.recv(8))):
                            self.clientsocket.send(ret)
                        else:
                            s.close()
                            self.read_list.remove(s)
        except select.error, v:
            if v[0] != errno.EINTR:
                print "ERREUR FATALE"
                raise
            else:
                self.reloadConfig(None, None)

    def makeLoop( self ):
        try:
            while (42):
                if not 'programs' in self.conf:
                    raise NameError("No 'programs' in configuration")
                self.serverListen()
                self.managePrograms()

        except KeyboardInterrupt:
            exiting()

    def getConfig( self ):
        sendConf = self.conf.copy()

        for (key, value) in sendConf['programs'].items():
            if 'processes' in value:
                sendConf['programs'][key].pop("processes", None)

        serializedConf = pickle.dumps(sendConf)
        return serializedConf

    def execInstruct( self, instruct ):
        if (re.match("list", instruct)):
            return self.listProg()
        elif (re.match("shutdown", instruct)):
            return self.shutdown()
        elif (re.match("start_all", instruct)):
            return self.startAll()
        elif (re.match("stop_all", instruct)):
            return self.stopAll()
        elif (re.match("start ", instruct)):
            return self.start(instruct[6:])
        elif (re.match("stop ", instruct)):
            return self.stop(instruct[5:])
        elif (re.match("restart ", instruct)):
            return self.restart(instruct[8:])
        elif (re.match("info ", instruct)):
            return self.info(instruct[5:])
        elif (re.match("info", instruct)):
            return self.listProg()
        elif (re.match("getConfig", instruct)):
            return self.getConfig()
        elif (re.match("reload", instruct)):
            return self.reloadConfig(None, None)
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

    def shutdown( self ): #Exit le serveur proprement apres avoir stoppe le reste
        ret = "Shutting down"
        self.clientsocket.send(str(len(ret)))
        if (len(self.clientsocket.recv(8))):
            self.clientsocket.send(ret)
        self.stopAll()
        print ret
        exiting()
        return ""

    # def launchProg( self, progName, progConf, nbRetries, nbProcess = None ):
    def startAll( self ): #Starte tous les programmes # A REFAIRE
        ret = "Starting all programs :\n"
        for (key, value) in self.conf['programs'].items():
            ret += self.startingProgram(key, value)
        return ret


    def stopAll( self ):
        ret = "Stopping all programs :\n"
        for (key, value) in self.conf['programs'].items():
            ret += self.exitingProg(key, value)
        return ret

    def start( self, name ):
        ret = ""
        if name in self.conf['programs']:
            ret += self.startingProgram(name, self.conf['programs'][name])
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret

    def restart( self, name ):
        ret = ""
        if name in self.conf['programs']:
            ret += self.exitingProg(name, self.conf['programs'][name])
            ret += self.startingProgram(name, self.conf['programs'][name])
        else:
            ret += name + PROGRAM_NOT_FOUND
        return ret

    def stop( self, name ):
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

    def managePrograms( self ):
        for (key, value) in self.conf['programs'].items():
            dateNow = datetime.now()
            if 'processes' in value and len(value['processes']) > 0:
                for process in value['processes']:
                    if process['status'] is FAILED or process['status'] is EXITED:
                        continue
                    returnValue = process['process'][1].poll()
                    # PROCESS IS RUNNING
                    if returnValue is None:
                        if process['status'] is LAUNCHED:
                            dateDiff = (dateNow - process['process'][0]).total_seconds()
                            if dateDiff >= value['starttime']:
                                process['status'] = RUNNING
                        elif process['status'] is STOPPING:
                            dateDiff = (dateNow - process['stoptime']).total_seconds()
                            if dateDiff >= value['killtime']:
                                process['process'][1].send_signal(SIGKILL)
                                process['status'] = FAILED
                    # PROCESS IS NOT RUNNING
                    else:
                        if process['status'] is LAUNCHED:
                            dateDiff = (dateNow - process['process'][0]).total_seconds()
                            if (returnValue not in value['exitcodes'] or dateDiff < value['starttime']) and value['autorestart'] is not 'never':
                               self.relaunchProg(key, value, process)
                            else:
                                process['status'] = EXITED
                        elif process['status'] is RUNNING:
                            if value['autorestart'] == 'always' or (value['autorestart'] == 'unexpected' and returnValue not in value['exitcodes']):
                                value['processes'].remove(process)
                                self.launchProg(key, value, value['startretries'], 1)
                            else:
                                if returnValue not in value['exitcodes']:
                                    process['status'] = FAILED
                                else:
                                    process['status'] = EXITED
                        elif process['status'] is STOPPING:
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
            proc = psutil.Popen(progConf['cmd'].split(), env=dict(env), stderr=errProg, stdout=outProg, stdin=inProg, cwd=workingDir)

            date = datetime.now()
            progConf['processes'].append({'process' : (date, proc), 'status' : LAUNCHED, 'retries' : nbRetries, 'stoptime' : None})
            verbose += "pid : " + str(proc.pid) + date.strftime(", started at %H:%M:%S %a, %d %b %Y") + "\n"

        if self.conf["args"].verbose:
            print verbose

        if self.logFile is not None:
            self.logFile.write(verbose)

        if 'umask' in progConf:
            os.umask(oldMask)

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


#reload SIGHUP configuration =(

# ajout timeout cote client quand il ne recoit pas de reponse du serv

# verifier les droits des fichiers de log

# verifier que toutes les actions (sauf liste etc..) sont logges

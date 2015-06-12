#!/usr/bin/python

from taskmaster import _TaskMaster

import yaml
import argparse
import subprocess
import sys
import psutil
import datetime
import time
import os
import atexit
import errno
import socket
import pickle
from socket import error as socket_error
from signal import SIGTERM
from exit import Scolors

UNIX_SOCKET_PATH = "/tmp/taskmaster_unix_socket"
PID_FILE = "/tmp/taskmaster.pid"
CONF_FILE = "config.yaml"
DEV_NULL = "/dev/null"

def delPid():
    os.remove(PID_FILE)

def startDaemon():
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

        # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(DEV_NULL, 'r')
    so = file(DEV_NULL, 'a+')
    se = file(DEV_NULL, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # write pidfile
    atexit.register(delPid)
    pid = str(os.getpid())
    file(PID_FILE,'w+').write("%s\n" % pid)

def getTaskPid():
    try:
        pidFile = file(PID_FILE, 'r')
        pid = int(pidFile.read().strip())
        pidFile.close()
    except IOError:
        pid = None
    return pid

def daemonize():
    pid = getTaskPid()
    if pid:
        message = Scolors.RED + "pidfile %s already exist. Tasmaster already running ?\n" + Scolors.ENDC
        sys.stderr.write(message % PID_FILE)
        sys.exit(1)
    startDaemon()

def taskMasterStop():
    """Stop the TaskMaster"""
    pid = getTaskPid()
    if not pid:
        message = Scolors.RED + "pidfile %s does not exist, Taskmaster not running in daemon?\n" + Scolors.ENDC
        sys.stderr.write(message % PID_FILE)
        return
    try:
        while 42:
            os.kill(pid, SIGTERM)
            time.sleep(0.1)
    except OSError, err:
        err = str(err)
        if err.find("No such process") > 0:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            else:
                print str(err)
                sys.exit(1)

def taskMasterStart( conf ):
    """Start the taskmaster"""
    if conf["args"].daemon:
        daemonize()
    taskMaster = _TaskMaster(conf)
    taskMaster.runTaskMaster()

def taskMasterRestart( args ):
    """Restart the taskmaster"""
    conf = {}
    newConf = getConfig(args, False)
    pid = getTaskPid()
    if pid:
        try:
            clientsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            clientsocket.connect(UNIX_SOCKET_PATH)
            clientsocket.send("getConfig") #envoie instruction
            buf = clientsocket.recv(8)#recup length de la future reception
            if(int(buf)):
                clientsocket.send("OK") #envoie instruction
                buf = clientsocket.recv(int(buf))
                if len(buf) > 0:
                    conf = pickle.loads(buf)
                    if "args" in conf:
                        newConf["args"] = conf["args"]
        except socket_error as serr:
            if serr.errno != errno.ECONNREFUSED:
                raise serr
            print Scolors.RED + "Can't connect to daemon to retreive config file." + Scolors.ENDC

        print conf
        for (key, value) in newConf.items():
            if not key in conf:
                conf[key] = value
            else:
                if isinstance(conf[key], dict):
                    conf[key].update(value)

    else:
        conf = newConf

    taskMasterStop()
    taskMasterStart(conf)

def getConfig( args, errorConfig=True ):
    conf = {}
    configurationFiles = []
    if args.configuration_file:
        for _file in args.configuration_file:
            openConf = yaml.load(open(_file, 'r'))
            configurationFiles.append(os.path.abspath(_file))
            for (key, value) in openConf.items():
                if not key in conf:
                    conf[key] = value
                else:
                    conf[key].update(value)
    else:
        try:
            _file = open(CONF_FILE, 'r')
            configurationFiles.append(os.path.abspath(CONF_FILE))
            conf = yaml.load(_file)
        except IOError:
            if errorConfig:
                print Scolors.RED + "Taskmaster can't find any configuration file" + Scolors.ENDC
                sys.exit()
    conf["originalWD"] = os.getcwd()
    conf["args"] = args
    conf["configurationFiles"] = configurationFiles
    return conf


def main():
    # try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--daemon", help="run program as daemon", action="store_true")
        parser.add_argument("-v", "--verbose", help="talk a lot", action="store_true")
        parser.add_argument("--stop", help="stop the program", action="store_true")
        parser.add_argument("--start", help="start", action="store_true")
        parser.add_argument("--restart", help="restart", action="store_true")
        parser.add_argument("-c", "--configuration-file", nargs='+', help="allow user to load specific configuration(s) file(s)")
        args = parser.parse_args()
        if args.start or (not args.stop and not args.restart):
            conf = getConfig(args)
            taskMasterStart(conf)
            if args.stop:
                taskMasterStop()
                if args.restart:
                    taskMasterRestart(args)
    # except:
    #     # print Scolors.GREEN + "Exited" + Scolors.ENDC
    #     print "FAIL error in main : ", sys.exc_info()[1]

main()

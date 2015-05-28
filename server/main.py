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

from exit import Scolors

PID_FILE = "/tmp/taskmaster.pid"
CONF_FILE = "conf.yaml"
DEV_NULL = "/dev/null"

def delPid():
    os.remove(PID_FILE)

def startDaemon():
    # print "YOLO"
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


def daemonize():
    # print "D-MON"
    try:
        pidFile = file(PID_FILE, 'r')
        pid = int(pidFile.read().strip())
        pidFile.close()
    except IOError:
        pid = None
    if pid:
        message = Scolors.RED + "pidfile %s already exist. Daemon already running ?\n" + Scolors.ENDC
        sys.stderr.write(message % PID_FILE)
        sys.exit(1)
    startDaemon()

def main():
    # try:
    conf = {}
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--daemon", help="run program as daemon", action="store_true")
    parser.add_argument("-v", "--verbose", help="talk a lot", action="store_true")
    # NE MARCHE PAS COMME VOULU :
    # parser.add_argument("stop", help="stop", action="store_false")
    # parser.add_argument("start", help="start", action="store_false")
    # parser.add_argument("restart", help="restart", action="store_false")
    # rajouter start et stop ?? les gerer de la
    parser.add_argument("-c", "--configuration-file", nargs='+', help="allow user to load specific configuration file")
    args = parser.parse_args()
    # if args.stop:
    #     print "STOP"
    # if args.start:
    #     print "START"
    # if args.restart:
    #     print "RESTART"
    if args.configuration_file:
        for _file in args.configuration_file:
            openConf = yaml.load(open(_file, 'r'))
            for (key, value) in openConf.items():
                if not key in conf:
                    conf[key] = value
                else:
                    conf[key].update(value)
    else:
        try:
            _file = open(CONF_FILE, 'r')
            conf = yaml.load(_file)
        except IOError:
            print Scolors.RED + "Taskmaster can't find any configuration file" + Scolors.ENDC
            sys.exit()
    # print "HERE"
    if args.daemon:
        daemonize()
    # print "THERE"
    taskMaster = _TaskMaster(conf, args)
    taskMaster.runTM()
    # except:
    #     print "FAIL error in main : ", sys.exc_info()[1]
main()

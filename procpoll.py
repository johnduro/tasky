#!/usr/bin/python

import yaml
import subprocess
import sys
import psutil

from subprocess import call


proc0 = psutil.Popen(["cat"])
proc1 = psutil.Popen(["cat"])
proc2 = psutil.Popen(["ls"])
proc3 = psutil.Popen(["cat"])
proc4 = psutil.Popen(["cat"])

while (proc0.poll() == None):
    print proc0.pid

a = proc0.poll()

if (a == 1):
    print 'lol'
else:
    print a



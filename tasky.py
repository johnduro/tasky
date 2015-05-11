#!/usr/bin/python

import yaml
import subprocess
import sys

from subprocess import call


programs = open("config.yaml", 'r')

lol = yaml.load(programs)

try:
    out = subprocess.check_output(["cat"], "*", shell=True)
    l = subprocess.check_call()
    print out
    print l
except:
    print "wrong command", sys.exc_info()

try:
    out = subprocess.check_output(["echosd", "Hello World!"])
    print out
except:
    print "wrong command", sys.exc_info()

try:
    out = subprocess.check_output(["echo", "Hello World!"])
    print out
except:
    print "wrong command:", sys.exc_info()

            #call(["ls", "-l"])

print lol['programs']['nginx']


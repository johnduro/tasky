#!/usr/bin/python
import yaml
from subprocess import call

programs = open("config.yaml", 'r')
lol = yaml.load(programs)
# call(["ls", "-l"])
print lol['programs']['nginx']['autorestart']


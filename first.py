
#!/usr/bin/python

import yaml
import subprocess
import sys
import psutil

from subprocess import call


def main():
    programs = open("config.yaml", 'r')
    proglist = yaml.load(programs)


if __name__ == "__main__":
    main()


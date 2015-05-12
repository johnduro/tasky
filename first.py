
#!/usr/bin/python

import yaml
import argparse
# import subprocess
import sys
# import psutil

from subprocess import call

class _TaskMaster:
    """class for program management"""
    def __init__(self, conf):
        self.conf = conf

    def runTM(self):
        self.initFirstLaunch()

    def initFirstLaunch(self):
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")

def main():
    # programs = open("config.yaml", 'r')
    # proglist = yaml.load(programs)
    try:
        conf = {}
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--daemon", help="run program as daemon", action="store_true")
        parser.add_argument("-c", "--configuration-file", nargs='+', help="allow user to load specific configuration file")
        args = parser.parse_args()
        if args.configuration_file:
            for _file in args.configuration_file:
                openConf = yaml.load(open(_file, 'r'))
                for (key, value) in openConf.items():
                    # print key
                    if not key in conf:
                        conf[key] = value
                    else:
                        conf[key].update(value)
        # print conf
        taskMaster = _TaskMaster(conf)
        taskMaster.runTM()
    except:
        print "FAIL error in main : ", sys.exc_info()[1]


if __name__ == "__main__":
    main()


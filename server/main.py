from taskmaster import _TaskMaster

import yaml
import argparse
import subprocess
import sys
import psutil
import datetime
import time
import os

from exit import Scolors

def main():
    # try:
    conf = {}
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--daemon", help="run program as daemon", action="store_true")
    parser.add_argument("-v", "--verbose", help="talk a lot", action="store_true")
    parser.add_argument("-c", "--configuration-file", nargs='+', help="allow user to load specific configuration file")
    args = parser.parse_args()
    if args.configuration_file:
        for _file in args.configuration_file:
            openConf = yaml.load(open(_file, 'r'))
            for (key, value) in openConf.items():
                if not key in conf:
                    conf[key] = value
                else:
                    conf[key].update(value)
    taskMaster = _TaskMaster(conf, args)
    taskMaster.runTM()
    # except:
    #     print "FAIL error in main : ", sys.exc_info()[1]
main()
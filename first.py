
#!/usr/bin/python

import yaml
import argparse
import subprocess
import sys
import psutil
import datetime
import time

from subprocess import call

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf ):
        # self.conf = {}
        self.conf = conf

    def runTM( self ):
        # print "HERE"
        self.initFirstLaunch()
        # print "THERE"
        self.makeLoop()
        # print "HOHO"
        # for (key, value) in self.conf['programs'].items():
        #     for prog in value['proX']:
        #         print prog[0]
        #         print prog[1].pid
        #         if prog[1].poll():
        #             print "running"

    def makeLoop( self ):
        while (42):
            # print "in loop"
            if not 'programs' in self.conf:
                raise NameError("No 'programs' in configuration")
            else:
                self.managePrograms(self.conf['programs'])
            # print "out loop"

    def managePrograms( self, programs ):
        # print "in manage"
        for (key, value) in programs.items():
            print key
            for proX in value['proX']:
                poll = proX[1].poll()
                print "POLL"
                print poll
                if poll != None:
                    if value['autoRestart'] == 'always':
                        # print "ALWAYS"
                        proX = (datetime, psutil.Popen(value['cmd'].split()))
                    elif value['autoRestart'] == 'never':
                        continue
                    elif value['autoRestart'] == 'unexpected':
                        # print "UNEXPECTED"
                        if poll not in value['exitCodes']:
                            proX = (datetime, psutil.Popen(value['cmd'].split()))


    def initFirstLaunch( self ):
        """lance tous les programs contenus dans self.conf['programs']"""
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")
        else:
            for (key, value) in self.conf['programs'].items():
                value['proX'] = []
                value['proX'].append((datetime, psutil.Popen(value['cmd'].split())))
                # value['proX']['pList'].append()

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


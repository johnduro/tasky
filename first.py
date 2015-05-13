
#!/usr/bin/python

import yaml
import argparse
import subprocess
import sys
import psutil
import datetime
import time
import os

from subprocess import call

# rajouter une valeur 'status' dans les dict pour savoir ou on en est
# retirer les process de la liste quand ils sont termines et traites ?
# umask ne fonctionne pas

class _TaskMaster:
    """class for program management"""
    def __init__( self, conf, args ):
        self.conf = conf
        self.args = args

    def runTM( self ):
        self.initFirstLaunch()
        self.makeLoop()

    def makeLoop( self ):
        while (42):
            if not 'programs' in self.conf:
                raise NameError("No 'programs' in configuration")
            else:
                self.managePrograms(self.conf['programs'])

    def managePrograms( self, programs ):
        for (key, value) in programs.items():
            #print key #p
            for proX in value['proX']:
                returnValue = proX[1].poll()
                #print "POLL" #p
                #print returnValue #p
                #print proX[1].pid #p
                if returnValue != None:
                    if value['autorestart'] == 'always' or value['autorestart'] == 'unexpected':
                        if value['startretries'] > 0 and returnValue not in value['exitcodes'] or value['autorestart'] == 'always':
                            self.relaunchProg(key, value)
                            # proX.append((datetime, psutil.Popen(value['cmd'].split())))
                        else:
                            self.exitingProg(key, value, returnValue)
                    elif value['autorestart'] == 'never':
                        continue


    def initFirstLaunch( self ):
        """lance tous les programs contenus dans self.conf['programs']"""
        if not 'programs' in self.conf:
            raise NameError("No 'programs' in configuration")
        else:
            for (key, value) in self.conf['programs'].items():
                value['proX'] = []
                if value['autostart'] == True:
                    self.launchProg(key, value)

    def exitingProg( self, progName, progConf, returnValue):
        """lance les processus de progName avec la configuration dans progConf"""
        if self.args.verbose:
            print "exiting " + progName + " pid : " + str(progConf['proX'][0][1].pid) + " with return code " + str(returnValue)
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])

        progConf['proX'] = []
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)

    def relaunchProg( self, progName, progConf):
        """lance les processus de progName avec la configuration dans progConf"""
        progConf['startretries'] -= 1
        if self.args.verbose:
            print "ReLaunching process : " + progName
            print "remaining retry : " + str(progConf['startretries'])
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])
        progConf['proX'] = []
        progConf['proX'].append((datetime, psutil.Popen(progConf['cmd'].split())))
        if self.args.verbose:
            print "pid : " + str(progConf['proX'][0][1].pid)
        #self.launchProg(progName, progConf)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)


    def launchProg( self, progName, progConf):
        """lance les processus de progName avec la configuration dans progConf"""
        if self.args.verbose:
            print "Launching process : " + progName
        # if 'umask' in progConf:
        #     print "UMSK FIRST"
        #     print int(str(progConf['umask']), 8)
        #     oldMask = os.umask(progConf['umask'])
        progConf['proX'].append((datetime, psutil.Popen(progConf['cmd'].split())))
        if self.args.verbose:
            print "pid : " + str(progConf['proX'][0][1].pid)
        # if 'umask' in progConf:
        #     print "UMSK SECOND"
        #     print oldMask
        #     os.umask(oldMask)


def main():
    try:
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
    except:
        print "FAIL error in main : ", sys.exc_info()[1]


if __name__ == "__main__":
    main()


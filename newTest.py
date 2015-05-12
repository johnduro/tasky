# #!/usr/bin/python

# import yaml
# import subprocess
# import sys
# import psutil


# config = open("config.yaml", 'r')
# configYaml = yaml.load(config)

# programs = {'taskmaster' : {'hoho' : 1, 'haha' : 2}, 'childs' : configYaml['programs'] }

# programs['childs']['nginx']['proX'] = psutil.Popen(["cat"])

# dict_ = {'1':1, 2:'2'}
# list_ = [1, 2, 3]

#!/usr/bin/python

import yaml
import subprocess
import sys
import psutil

from subprocess import call


programs = open("config.yaml", 'r')
proglist = yaml.load(programs)

# for (slug, title) in proglist['programs'].items():
for (key, value) in proglist['programs'].items():
    #  print slug
    #  print title['cmd']
    value['proX'] = psutil.Popen(value['cmd'])

while (1):
    for (slug, title) in proglist['programs'].items():
        a = title['proX'].poll()
        if (a != None and title['autorestart'] != None):
            if (a == -9):
                sys.exit(0)
            else:
                title['proX'] = psutil.Popen(title['cmd'])
        if (a == None):
            print title['proX'].pid

                # a = proc0.poll()

                # if (a == 1):
                #     print 'lol'
                # else:
                #     print a


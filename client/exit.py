import sys
from scolors import Scolors

def exit_query():
    answer = query_yes_no("Do you really want to exit ?");
    if answer == 1:
        exiting()

def exiting():
    print Scolors.GREEN + "\nExiting Client..." + Scolors.ENDC
    exit()

def query_yes_no(question):
    try :
        prompt = " [y/n] "
        while True:
            print question + prompt
            choice = raw_input().lower()
            if choice == 'yes' or choice == 'y':
                return 1
            elif choice == 'no' or choice == 'n':
                return 0
            else:
                print Scolors.RED + "Please respond with 'yes' or 'no' (or 'y' or 'n')." + Scolors.ENDC
    except KeyboardInterrupt:
        exiting()
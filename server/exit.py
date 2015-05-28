#!/usr/bin/python

class Scolors:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[36m'
    GREEN = '\033[92m'
    PURPLE = '\033[35m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    GREY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'


def exiting():
    print Scolors.GREEN + "\nServer shutting down..." + Scolors.ENDC
    exit()
##Email checker - New messages notifier

###Requirements:

- IMAP access
- [Python 3.3+](http://www.python.org/) (if not using a build)
- [gntp Python library](http://pythonhosted.org/gntp/) (if not using a build)
- a running notification application supporting the GNTP protocol, e.g. Growl
  and its ports

###Info:

Just a very simple script, without any interaction with the user. To end it, 
just kill it.

Tested with Gmail and Outlook, Windows 7 (Growl for Windows) and Linux 
Mint 15 (Growl For Linux).

A configuration file is needed (default: _settings.ini_). Some of the 
settings can be specified from command line.

###Comand line options

    usage: email checker [-h] [-V] [-v] [-s SETTINGS] [-p PROFILE] [-u USER]
                         [-x PASS]
    optional arguments:
      -h, --help            show this help message and exit
      -V, --version         show program's version number and exit
      -v, --verbose         show detailed info
      -s SETTINGS, --settings SETTINGS
                            specify a custom settings file path
      -p PROFILE, --profile PROFILE
                            choose a profile from the settings file
      -u USER, --user USER  specify the user
      -x PASS, --pass PASS  specify the password

###Changelog:

    0.1 [2013-11-10]: initial release

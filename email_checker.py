#!/usr/bin/env python3
"""Email checker - New messages notifier

Requirements:
- IMAP access
- Python 3.3+ <http://www.python.org/> (if not using a build)
- gntp Python library <http://pythonhosted.org/gntp/> (if not using a build)
- a running notification application supporting the GTNP protocol, e.g. Growl
  and its ports

Just a very simple script, without any interaction with the user. To end it, 
just kill it.

Tested with Gmail and Outlook, Windows 7 (Growl for Windows) and Linux 
Mint 15 (Growl For Linux).

A configuration file is needed (default: settings.ini). Some of the 
settings can be specified from command line:

  usage: email_checker.py [-h] [-V] [-v] [-s SETTINGS] [-p PROFILE] [-u USER]
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

Changelog:
  0.1 [2013-11-10]: initial release


Homepage: <https://github.com/vdcrim/email_checker>


Copyright (C) 2013  Diego Fernández Gosende <dfgosende@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along 
with this program.  If not, see <http://www.gnu.org/licenses/gpl-3.0.html>.

"""

import os.path
import re
from collections import defaultdict
import imaplib
import email.parser, email.header
from datetime import datetime, timezone
import time
import threading
import configparser
import argparse

import gntp.notifier

# Application info
name = 'email checker'
version = '0.1'
description = 'New messages notifier'
url = 'https://github.com/vdcrim/email_checker'
license = 'GNU GPL v3'

# IMAP reference: <http://tools.ietf.org/html/rfc3501.html>


class EmailChecker(object):
    
    def __init__(self, config_path=None):
        self.config = configparser.ConfigParser(
                                default_section='default', allow_no_value=True)
        self.config['general'] = {'config_path': 'settings.ini'}
        if config_path is not None:
            self.read_config(config_path)
        self.uid_dict = defaultdict(int) # TODO: UIDVALIDITY
        self.re_list_response = re.compile(br'\((.*?)\)\s+"(.*?)"\s+(.*)')
        self.parse_header = email.parser.BytesHeaderParser().parsebytes
        self._thread = None
        self._cancel = threading.Event()
        self._err = None
    
    def parse_command_line(self):
        epilog = 'Latest version: <{url}>\n\nLicense: {license}'.format(
                                                    url=url, license=license)
        parser = argparse.ArgumentParser(prog=name, description=description, 
            epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument('-V', '--version', action='version', 
                            version='{} v{}'.format(name, version))
        parser.add_argument('-v', '--verbose', action='store_true', 
                            help='show detailed info')
        parser.add_argument('-s', '--settings', 
                            help='specify a custom settings file path')
        parser.add_argument('-p', '--profile', 
                            help='choose a profile from the settings file')
        parser.add_argument('-u', '--user', help='specify the user')
        parser.add_argument('-x', '--pass', help='specify the password', 
                            dest='pass_', metavar='PASS')
        args = parser.parse_args()
        self.read_config(args.settings)
        self.config['general']['verbose'] = str(args.verbose or __debug__)
        if args.profile is not None:
            self.config['general']['profile'] = args.profile
            self.profile = self.config[args.profile]
        if args.user is not None:
            self.profile['user_id'] = args.user
        if args.pass_ is not None:
            self.profile['password'] = args.pass_
    
    def read_config(self, config_path=None):
        if config_path is not None:
            self.config['general']['config_path'] = config_path
        self.config.read(self.config['general']['config_path'])
        self.profile = self.config[self.config['general']['profile']]
        self.config.excluded_mailboxes_names = \
            self.config['excluded mailboxes / names'].values()
        self.config.excluded_mailboxes_flags = \
            self.config['excluded mailboxes / flags'].values()
        if __debug__: # always show info with no python -O flag
            self.config['general']['verbose'] = 'yes'
    
    def register_gntp(self):
        self.growl_notifier = gntp.notifier.GrowlNotifier(
            applicationName=self.config['general']['profile'],
            notifications=['New email'],
            defaultNotifications=['New email'],
            applicationIcon=self._get_icon())
        self.growl_notifier.register()
    
    def _get_icon(self):
        """gntp library only admits http:// URIs and binary data"""
        if os.path.isfile(self.profile['icon']):
            with open(self.profile['icon'], 'rb') as icon_file:
                return icon_file.read()
        else:
            return self.profile['icon']
        
    
    def notify(self, title, description):
        return self.growl_notifier.notify('New email', title, description, 
                                          sticky=self.profile['sticky'], 
                                          priority=1, 
                                          callback=self.profile['url'])
    
    def login(self):
        try:
            self.mail = imaplib.IMAP4_SSL(self.profile['hostname'], 
                                          int(self.profile['port']))
        except OSError as err:
            try:
                period = self.profile.getboolean('period')
            except ValueError:
                period = True
            if period:
                if self.config['general'].getboolean('verbose'):
                    print('\n' + str(err))
                self._thread = threading.Timer(self.profile.getint('period'), 
                                               self._do_check)
                self._thread.daemon = True
                self._thread.start()
                return
            else:
                self._err = str(err)
                self._cancel.set()
                return
        try:
            ok, message = self.mail.login(self.profile['user_id'], 
                                          self.profile['password'])
        except imaplib.IMAP4.error as err:
            self._err = err.args[0]
            self._cancel.set()
            return
        if ok != 'OK':
            self._err = message[0].decode()
            self._cancel.set()
            return
        if self.config['general'].getboolean('verbose'):
            print('\n' + message[0].decode())
    
    def logout(self):
        bye, message = self.mail.logout()
        if self.config['general'].getboolean('verbose'):
            print('\n' + message[0].decode())
    
    def check(self, period=None):
        # update period
        if period == False:
            self.profile['period'] = 'no'
        elif period and period != True:
            self.profile['period'] = str(period)
        if self.config['general'].getboolean('verbose'):
            print('\nperiod:', self.profile['period'])
        # start checking
        self._thread = threading.Thread(target=self._do_check, daemon=True)
        self._thread.start()
    
    def _do_check(self):
        verbose = self.config['general'].getboolean('verbose')
        if verbose:
            print('\nchecking...', datetime.now(timezone.utc).astimezone())
        # get list of mailboxes
        try:
            ok, mblist = self.mail.list()
        except (imaplib.IMAP4.abort, ConnectionAbortedError) as err:
            if verbose:
                print(err)
            time.sleep(10)
            self.login()
            if self._cancel.is_set():
                return
            ok, mblist = self.mail.list()
        except imaplib.IMAP4.error as err:
            self._err = err.args[0]
            self._cancel.set()
            return
        # check every mailbox
        for mailbox in mblist:
            if self._cancel.is_set():
                return
            # select mailbox, if it's not excluded
            flags, delimiter, mailbox = self._parse_list_response(mailbox)
            for flag in flags:
                if flag in self.config.excluded_mailboxes_flags or \
                   flag == r'\Noselect':
                        continue_ = True
                        break
            else: continue_ = False
            if continue_ or mailbox.strip(b'"').decode('utf-7') in \
                    self.config.excluded_mailboxes_names:
                continue
            try:
                ok, data = self.mail.select(mailbox, readonly=True)
            except imaplib.IMAP4.abort as err:
                self._thread = threading.Thread(target=self._do_check, 
                                                daemon=True)
                self._thread.start()
                return
            # search for new unread messages
            # UIDNEXT is the starting UID for the next check
            uidnext = self.uid_dict[mailbox]
            ok, new_uidnext = self.mail.response('UIDNEXT')
            self.uid_dict[mailbox] = int(new_uidnext[0])
            if uidnext:
                search_criteria = '(UNSEEN UID {}:*)'.format(uidnext)
            else:
                search_criteria = '(UNSEEN)'
            ok, data = self.mail.uid('SEARCH', None, search_criteria)
            if verbose:
                print(mailbox.strip(b'"').decode('utf-7'), uidnext, data[0])
            if not data[0]:
                self.mail.close()
                continue
            if self._cancel.is_set():
                self.mail.close()
                return
            # parse headers for 'From' and 'Subject' and 
            # notify Growl about the new messages
            uids = data[0].decode().split()
            if int(uids[-1]) < uidnext: # because IMAP
                self.mail.close()
                continue
            ok, data = self.mail.uid('FETCH', '{}:*'.format(uids[0]), 
                                     '(BODY.PEEK[HEADER])')
            if verbose: print('')
            for header in data[::2]:
                if self._cancel.is_set():
                    self.mail.close()
                    return
                header = self.parse_header(header[1])
                from_ = self._decode_header(header['From'])
                subject = self._decode_header(header['Subject'])
                if verbose:
                    print('From: {}\nSubject: {}\n'.format(from_, subject))
                self.notify(from_, subject)
            self.mail.close()
        # schedule a new check
        try:
            period = self.profile.getboolean('period')
        except ValueError:
            period = True
        if period:
            self._thread = threading.Timer(self.profile.getint('period'), 
                                           self._do_check)
            self._thread.daemon = True
            self._thread.start()
    
    def _parse_list_response(self, line):
        flags, delimiter, mailbox_name = \
                                    self.re_list_response.match(line).groups()
        return flags.decode().split(), delimiter, mailbox_name
    
    def _decode_header(self, raw_header):
        header = ''
        for header_part, header_part_charset in \
                                        email.header.decode_header(raw_header):
            if header_part_charset is not None:
                header += header_part.decode(header_part_charset)
            elif isinstance(header_part, bytes):
                header += header_part.decode()
            else:
                header += header_part
        return header
    
    def wait(self):
        while not self._cancel.is_set():
            if self._cancel.wait(2) and self._err:
                raise SystemExit(self._err)
    
    def cancel(self):
        self._cancel.set()
        if hasattr(self._thread, 'cancel'):
            self._thread.cancel()
        self._thread.join(10)
        try: self.logout()
        except: pass


if __name__ == '__main__':
    
    email_checker = EmailChecker()
    email_checker.parse_command_line()
    email_checker.register_gntp()
    email_checker.login()
    email_checker.check()
    try:
        email_checker.wait()
    except (KeyboardInterrupt, SystemExit) as err:
        email_checker.cancel()
        raise SystemExit(err)


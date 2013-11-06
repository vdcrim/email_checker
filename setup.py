#!/usr/bin/env python3
"""Setup script for building an executable

Requirements:
- Python 3.3+ <http://www.python.org/>
- cx_Freeze <http://cx-freeze.sourceforge.net/>
- on Windows, the right Microsoft Visual C runtime DLLs (installed with Python)

Optional:
 - pywin32 <http://starship.python.net/crew/mhammond/win32/>
   For adding version resource on Windows 
 - UPX <http://upx.sourceforge.net/>
   This utility is used to compress the executable files.  Put the upx 
   executable in your PATH or set a custom filepath below.

A ZIP archive is generated with all needed resources.

You may need to read this if trying to build on (at least) Ubuntu 13.04:
<https://bitbucket.org/anthony_tuininga/cx_freeze/issue/32/cant-compile-cx_freeze-in-ubuntu-1304>


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

# optional executable icon
icon = 'icons/gmail.ico'

# optionally, compress executable files with UPX
upx_alt_path = r''


# ------------------------------------------------------------------------------


import sys, platform
import atexit
import os, os.path
import subprocess
import tempfile
import zipfile

try:
    import cx_Freeze
except ImportError:
    exit("\nCouldn't find cx_Freeze <http://cx-freeze.sourceforge.net/>")

sys.dont_write_bytecode = True
import email_checker

# Prepare a temporay directory
temp_dir = tempfile.TemporaryDirectory()
atexit.register(temp_dir.cleanup)
base_dir = os.path.join(temp_dir.name, email_checker.name)

# Set build options, include additional files
include_files=[['email_checker.py', 'src/email_checker.py'],
               ['setup.py', 'src/setup.py'],
               'settings.ini', 'copying.txt', 'icons/']
build_options = dict(build_exe=base_dir, 
    packages = [], include_files=include_files, 
    excludes = ['win32api', 'win32con', 'pywintypes', 'pyexpat'], 
    compressed=True, optimize=1, create_shared_zip=True, include_msvcr=True,
    )
if os.path.isfile(icon):
    build_options['icon'] = icon
if os.name == 'nt':
    base = 'Win32GUI' # no console
    name = email_checker.name + '.exe'
else:
    base = None
    name = email_checker.name
executables = [
    cx_Freeze.Executable('email_checker.py', base=base, targetName=name),
    ]

# Build executable and copy other files
# cx_Freeze doesn't currently support setting url and copyright info into exe
cx_Freeze.setup(name=email_checker.name,
      version = email_checker.version, 
      description = email_checker.name + ' - ' + email_checker.description,
      url=email_checker.url,
      license=email_checker.license,
      options = dict(build_exe=build_options),
      executables = executables,
      )
gntp_lib_license = 'gntp Python library license: MIT'
with open(os.path.join(base_dir, 'readme.txt'), 'w') as readme_file:
    readme_file.write('\n'.join((email_checker.__doc__, gntp_lib_license)))

# Compress the files with UPX, if available
if os.path.isfile(upx_alt_path):
    upx = upx_alt_path
else:
    which = 'where' if os.name == 'nt' else 'which'
    try:
        subprocess.check_call([which, 'upx'])
    except subprocess.CalledProcessError:
        upx = None
    else:
        upx = 'upx'
if upx is not None:
    args = [upx, '--best', '--no-progress']
    args.extend(os.path.join(base_dir, filename) for filename in 
        os.listdir(base_dir) if filename == name or 
        os.path.splitext(filename)[1].lower() in ('.exe','.dll','.pyd', '.so'))
    subprocess.call(args)
else:
    print("\nUPX not found")

# Create ZIP archive and delete the temporal directory
with zipfile.ZipFile('{} v{} ({} {} executable).zip'.format(email_checker.name, 
                        email_checker.version, platform.system(), 
                        'x86-64' if sys.maxsize > 2**32 else 'x86'), 
                     'w', compression=zipfile.ZIP_DEFLATED
                     ) as zip:
    for dirpath, dirnames, filenames in os.walk(base_dir):
        for filename in filenames:
            real_path = os.path.join(dirpath, filename)
            archive_path = os.path.relpath(real_path, temp_dir.name)
            zip.write(real_path, archive_path)
print('\nZIP file created')

input('\nPress a key to finish...')

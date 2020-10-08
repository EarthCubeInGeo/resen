# Script to replace the version numbers in all *.rst files EXCEPT HISTORY.rst

import re
import os
import fileinput

old_version = '2020.2.0'
new_version = '2020.1.0'

for root, dirs, files in os.walk('..'):
    for fn in files:
        if fn.endswith('.rst') and fn!='HISTORY.rst':

            filename = os.path.join(root,fn)
            with fileinput.FileInput(filename, inplace=True) as f:
                for line in f:
                    print(line.replace(old_version, new_version), end='')

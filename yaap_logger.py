#  Copyright 2018, University of California, Irvine
# 
#  Authors: Zhihao Yao, Ardalan Amiri Sani
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
# 
#      http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import re, sys

class shell:
	HEAD = '\033[95m'
	DEBUG = '\033[1;94m'
	WARNING = '\033[1;93m'
	GREEN = '\033[1;92m'
	ERROR = '\033[1;91m'

	END = '\033[0m'

def log_error(format, *arg):
	printf(shell.ERROR + "ERROR: " + format + shell.END, *arg)

def log_debug(format, *arg):
	printf(shell.DEBUG + "DEBUG: " + shell.END + format, *arg)

def log_debug_no_text(format, *arg):
	printf(shell.DEBUG + format + shell.END, *arg)

def log_warning(format, *arg):
	printf(shell.WARNING + "WARNING: " + shell.END + format, *arg)

def log_warning_no_text(format, *arg):
	printf(shell.WARNING + format + shell.END, *arg)

def log_info(format, *arg):
	printf(format, *arg)

def log_ok(format, *arg):
	printf(shell.GREEN + "OK " + shell.END + format, *arg)

def printf(format, *arg):
	if len(arg) == 0:
		print format
	else:
		print format % tuple(arg)

def regex_findall(p, s, multi_line = False):
	assert type(p) is str
	assert type(s) is str
	if multi_line:
		return re.findall(p, s, re.MULTILINE|re.DOTALL)
	else:
		return re.findall(p, s)

def regex_find_list(p, l):
	assert type(p) is str
	assert type(l) is list
	r = re.compile(p)
	return sorted(filter(r.match, l), key = len)

def get_command_line_args():
	result = {}
	argv = sys.argv
	while argv:
		if argv[0][0] == '-':
			result[argv[0]] = argv[1]
		argv = argv[1:]
	if '-i' not in result:
		result['-i'] = 'git.diff'
	if '-o' not in result:
		result['-o'] = 'out.diff'
	return result


class regex_matcher(object):
    def __init__(self, r):
        self._r = r

    def match(self, s):
        self._match = re.match(self._r, s)
        return self._match

    def has_match(self, s):
        return bool(self.match(s))

    def group(self, s, i):
        return self.match(s).group(i)
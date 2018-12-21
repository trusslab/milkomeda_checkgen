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

import re, sys, os, subprocess
from yaap_logger import *

class elf_so(list):
	def __init__(self, path, namespace = [], special_prefix = []):
		functionName = sys._getframe().f_code.co_name

		self._set_namespace(namespace)
		self._set_path_string(path)
		self._set_special_prefix(special_prefix)
		self._set_symbols()
		list.__init__(self, self._symbols)

	def get_symbols(self):
		return self._symbols

	def _dump_symbols(self):
		functionName = sys._getframe().f_code.co_name
		_READ_ELF =  "readelf -Ws "
		symbols = []

		cmd = _READ_ELF + self._path
		pipe = subprocess.Popen(cmd.split(), \
			stdout=subprocess.PIPE, \
			stderr=subprocess.STDOUT)
		outputs = pipe.communicate()[0]

		for line in outputs.splitlines():
			if len(line.strip()) <= 0 or not line.strip()[0].isdigit():
				continue
			if len(line.split()) == 7:
				continue
			if self._namespace == []:
				symbols.append(line.split()[7])
			elif self._number_of_regex_matched(self._namespace_regex, line) or \
				any((prefix in line) for prefix in self._special_prefix):
				symbols.append(line.split()[7])
			else:
				continue

		return symbols

	def _number_of_regex_matched(self, p, s):
		assert type(p) is str
		assert type(s) is str
		return len(re.findall(p, s))

	def _set_symbols(self):
		self._symbols = self._dump_symbols()

	def _set_special_prefix(self, special_prefix):
		self._special_prefix = special_prefix

	def _set_namespace(self, namespace):
		rg = ".*"
		for i in namespace:
			rg += i + ".*"
		self._namespace = namespace
		self._namespace_regex = rg

	def _set_path_string(self, path):
		self._path = self._abs_path(path)

	def _abs_path(self, path):
		return os.path.abspath(path)


class source(list):
	def __init__(self, path):
		functionName = sys._getframe().f_code.co_name
		if os.path.isfile(path):
			with open(path) as fd:
				content = fd.readlines()
			list.__init__(self, content)
		else:
			log_error("%s: invalid file", functionName)
			exit(0)

	def dump(self, path):
		functionName = sys._getframe().f_code.co_name
		with open(path, 'w') as fd:
			for c in self:
				print >> fd, c.rstrip()
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

import sys, re, os, itertools
from yaap_logger import *
from yaap_base import source
from collections import OrderedDict

REGEX_HANDLE_SIGNATURE = r'error::Error GLES2DecoderImpl::Handle(.*)\('
REGEX_HANDLE_RETURN = r'\s*return.*;'
REGEX_HANDLE_KERROR_RETURN = r'\s*return error::.*'
REGEX_HANDLE_RETURN_GROUP = r'\s*return( error::.*?);'
REGEX_REMOVE_CAST_CMD_DATA = r'const volatile gles2::cmds::[\w\W]*?static_cast<const volatile gles2::cmds::[\w\W]*?;'
REGEX_REMOVE_CMD_ARGS = r'\([\w\W]*?uint32_t immediate_data_size,[\w\W]*?\)'

REGEX_REMOVE_CMD_ARGS_CAST = r'(GL[^{;]*?) = .*?c\.(.*?);'
REGEX_REMOVE_CLIENT_MEMORY_CHKS = r'if \([^)]*?(result|bucket)[\w\W]*?\)[\w\W]*?{[\w\W]*?}'

LINE_TO_REMOVE = ['ExitCommandProcessingEarly;']
FUNCTION_EXCLUSIONS = ['CHROMIUM']

class handle(list):
	def __init__(self, data, paths):
		functionName = sys._getframe().f_code.co_name

		content = []
		for p in paths:
			if os.path.isfile(p):
				with open(p) as fd:
					content += fd.readlines()
			else:
				log_error("%s: invalid file", functionName)
				exit(0)
		list.__init__(self, content)
		self.data_ = data
		self.special_ = []

	def get_default_return_value(self, type_name):
		functionName = sys._getframe().f_code.co_name

		default_value = ''
		return {
			'GLenum': ' 0',
			'GLboolean': ' false',
			'GLuint': ' 0',
			'GLint': ' 0',
			'GLfloat': ' 0',
			'GLsizei': ' 0',
			'GLsync': ' 0',
			'void': ''
		}.get(type_name, default_value)

	def replace_return_type(self, line, type_name):
		functionName = sys._getframe().f_code.co_name

		return_regex = re.search(REGEX_HANDLE_RETURN_GROUP, line)
		if not return_regex:
			return line
		else:
			return line.replace(return_regex.group(1), \
				self.get_default_return_value(type_name))

	def get_function_args(self, body):
		functionName = sys._getframe().f_code.co_name

		args = ''
		matches = re.findall(REGEX_REMOVE_CMD_ARGS_CAST, body, flags = re.MULTILINE)
		for m in matches:
			args += m[0] + ', '
		return args[:-2]


	def get_all_handle(self):
		functionName = sys._getframe().f_code.co_name

		result = {}
		name = ""
		in_func = False
		prev_line = ""

		for i in range(len(self)):
			if not in_func:
				found = re.search(REGEX_HANDLE_SIGNATURE, self[i])
				if found and (found.group(1) in self.data_): 
					name = found.group(1)
					in_func = True
					api_return_type = self.data_[name]["return"]
					result[name] = self[i].replace("error::Error", api_return_type).\
						replace("GLES2DecoderImpl::Handle", "GLES2DecoderImpl::Milko_Handle_")
			else:
				if any(e in self[i] for e in LINE_TO_REMOVE):
					continue;

				curr_line = self[i]
				curr_line = self.replace_return_type(curr_line, self.data_[name]["return"])
				result[name] += curr_line
				if self[i].rstrip() == '}':
					in_func = False
					if not re.search(REGEX_HANDLE_KERROR_RETURN, prev_line):
						self.special_.append(name + ":" + prev_line)
			prev_line = self[i]
		return result

	def process_all_function_body(self, function_dict):
		result = {}
		for name, body in function_dict.iteritems():
			new_body = body
			new_body = re.sub(REGEX_REMOVE_CAST_CMD_DATA, '', new_body, flags = re.MULTILINE)
			new_body = re.sub(REGEX_REMOVE_CMD_ARGS, '', new_body, flags = re.MULTILINE)
			new_body = re.sub(REGEX_REMOVE_CLIENT_MEMORY_CHKS, '// removed client side buffer checks', new_body, flags = re.MULTILINE)
			new_args = self.get_function_args(new_body)
			new_body = new_body.replace(' {', '(' + new_args + ') {', 1)
			new_body = re.sub(REGEX_REMOVE_CMD_ARGS_CAST, '', new_body, flags = re.MULTILINE)
			new_body = re.sub(r'(  \n)+', '\n', new_body, flags = re.MULTILINE)
			result[name] = new_body
		return result
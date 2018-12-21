#! /usr/bin/python

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

import sys, re, os, itertools, subprocess
from yaap_logger import *
from yaap_base import elf_so, source
from yaap_handle_autogen import handle
from collections import OrderedDict


REGEX_BARE_GL_NAME = r'(decoder->)?(state->)?(api\(\)->)?(api->)?gl(.*)Fn'
REGEX_DIRECT_GL_NAME = r'(?<![\>\w\.])gl([A-Z].*?)(?=.*\()'
REGEX_UNUSED_VARS_1 = r'auto\*\ api\ =\ .*->api\(\);'

class android_gl2_source(source):
	def __init__(self, path):
		functionName = sys._getframe().f_code.co_name
		source.__init__(self, path)


class android_gl2_header(source):
	def __init__(self, path):
		functionName = sys._getframe().f_code.co_name
		source.__init__(self, path)

	def load_android_gles2_methods(self):
		functionName = sys._getframe().f_code.co_name
		result = {}
		c = self[:]
		c = [l.strip() for l in c]
		for i, l in enumerate(c):
			if "API_ENTRY" in l:
				signature = l.replace("API_ENTRY(", "").replace(")", "", 1)
				name = l[l.find("(") + 1: l.find(")")]
				return_type = l.split()[0]
				args_str = l[l.find("(", l.find(")") + 1) + 1: l.find(")", l.find(")") + 1)]
				args_dict = self._convert_args_str_to_diction(args_str)
				line_start = i + 1
				line_end = line_start + 3  
				result[name] = {"line": [line_start, line_end],
					"return": return_type,
					"args": args_dict,
					"args_str": args_str,
					"signature": signature}
		return result

	def _convert_args_str_to_diction(self, args_str):
		functionName = sys._getframe().f_code.co_name
		args_list = re.split("\ |,\ ",args_str)
		keywords = ["const", "*"]
		if len(args_list) == 1:
			args_dict = OrderedDict()
		else:
			while (self._check_for_keywords(keywords, args_list)):
				keyword = self._check_for_keywords(keywords, args_list)
				self._eliminate_args_keyword(keyword, args_list)
			
			args_list[::2], args_list[1::2] = args_list[1::2], args_list[::2]
			args_dict = OrderedDict(itertools.izip(*[iter(args_list)] * 2))
		return args_dict

	def _check_for_keywords(self, keywords, args_list):
		functionName = sys._getframe().f_code.co_name
		for i in args_list:
			if i in keywords:
				return i
		return False

	def _eliminate_args_keyword(self, keyword, args_list):
		functionName = sys._getframe().f_code.co_name
		i = args_list.index(keyword)
		args_list[i:i+2] = [' '.join(args_list[i:i+2])]


class gles_lib(elf_so):

	_SPECIAL_PREFIXES = ["milko_helper_gl"]
	_GLES2_NAMESPACE = ["gpu", "gles2", "GLES2DecoderImpl", "Handle"]

	def __init__(self, path_chr, path_lib):
		functionName = sys._getframe().f_code.co_name

		if not path_chr.endswith("/"):
			path_chr = path_chr + "/"

		if not path_lib.endswith(".so"):
			log_error("incorrect library path")
			exit(0)

		if not path_lib.startswith("/"):
			path_lib = path_chr + path_lib

		elf_so.__init__(self, path = path_lib, namespace = self._GLES2_NAMESPACE, special_prefix = self._SPECIAL_PREFIXES)


TEMPLATE = \
"""
_FUNC_SIGN
	LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    _RTN_TYPE (*checkedGL)(_ARG_TYPES) = reinterpret_cast<_RTN_TYPE(*)(_ARG_TYPES)>
      (dlsym(handle, "_SYMBOL_NAME"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else {_RETURN checkedGL(_ARGS); }
	LOGDBG1("%s: %s", __func__, "[1] success");
}
"""

TEMPLATE_CHR = \
"""
extern "C" __attribute__((visibility("default"))) _RTN_TYPE _MILKO_FUNCTION_NAME(_ARG_DEFS) {
  LOGDBG1("%s: [0]", __func__);
  _RETURNmilko_decoder_->_DO_FUNCTION_NAME(_ARGS);
}
"""

DIVIDER = "*" * 80

def find_substring(container, subs):
	for i in range(len(container)):
		if any(sub in container[i] for sub in subs):
			return i
	return -1

def replace_gl_function_name(f, r, group_num = 1):
	has_change = False
	src = source(f)
	for i in range(len(src)):
		if any(src[i].strip().startswith(e) for e in ["//", "DCHECK"]):
			continue
		if re.search(r, src[i]):
			src[i] = re.sub(r, "vendor" + re.search(r, src[i]).group(group_num), src[i])
			has_change = True
	if has_change:
		insert_line = find_substring(src, ['#include "gpu/command_buffer/service/', '#include "base/', '#include "ui/', '#include "build/', "#define "])
		if insert_line < 0:
			print f
			assert False
		src.insert(insert_line + 1, '#include "gpu/command_buffer/service/vendor_gl.h"')

	src.dump(f)


def dir_walk(directory, exceptions):
	pool = []
	for directory,_,files in os.walk(directory):
		for f in files:
			if not any(e in f for e in exceptions):
				pool.append(os.path.abspath(os.path.join(directory, f)))
	return pool

def replace_all_gl_name(directory):
	files = dir_walk(directory, ["vendor", "unittest", "passthrough"])
	for f in files:
		replace_gl_function_name(f, REGEX_DIRECT_GL_NAME)
	
gl_excepted_apis = ['__glGetString', '__glGetStringi', '__glGetBooleanv', '__glGetFloatv', '__glGetIntegerv', '__glGetInteger64v']

if __name__ == '__main__':
# steps:
# 1. nm library file
# 2. list all symbols by name
# 3. a for loop go over all opengl functions
# 4. exclude the one with different parameters and return type
# 5. add the code block to android gl.cpp

	chromium_gles = gles_lib("/home/zephyr/milkomeda/chromium_android/src", \
		"out/decoder3/libgpu.cr.so")
	chromium_gles_symbols = chromium_gles.get_symbols()

	chromium_gles_src = source("/home/zephyr/milkomeda/chromium_android/src/gpu/command_buffer/service/gles2_cmd_decoder.cc")

	gl2_header = android_gl2_header("/mnt/bullhead_milkomeda/frameworks/native/opengl/medalibs/GLES2/gl2_api.in")
	gl2_api = gl2_header.load_android_gles2_methods()

	gen = ""
	gen_export = ""
	chr_export = ""
	gen_chr = ""
	success_api = []
	success_handle_data = {}

	for api in gl2_api:
		api_name = api[4:] if api.startswith("__") else api[2:]
		handle_api_name = api_name
		matches = regex_find_list(".*Handle" + api_name + "E(?!XT).*", chromium_gles_symbols)
		matches_Bucket = regex_find_list(".*Handle" + api_name + "Bucket" + "E(?!XT).*", chromium_gles_symbols)
		matches_Immediate = regex_find_list(".*Handle" + api_name + "Immediate" + "E(?!XT).*", chromium_gles_symbols)
		if len(matches):
			pass
		elif len(matches_Bucket):
			handle_api_name += "Bucket"
			matches = matches_Bucket
		elif len(matches_Immediate):
			handle_api_name += "Immediate"
			matches = matches_Immediate

		if len(matches) and \
			api not in gl_excepted_apis:
			
			android_args = gl2_api[api]["args"]
			android_names = [i.replace("*", "") for i in android_args]
			android_types = [android_args[i] + ("*" if "*" in i else "") for i in android_args]
			args_def = []
			for a,b in zip(android_types,android_names):
				args_def.append(a + " " + b)

			rtn_t = gl2_api[api]["return"]
			gen += TEMPLATE.replace("_ARG_TYPES", ", ".join(android_types)) \
							.replace("_SYMBOL_NAME", "milko_" + api) \
							.replace("_ARGS", ", ".join(android_names)) \
							.replace("_FUNC_SIGN", gl2_api[api]["signature"]) \
							.replace("_RETURN", "" if rtn_t == "void" else "return") \
							.replace("_RTN_TYPE", rtn_t)
			gen_export += gl2_api[api]["signature"].replace(" {", ";").replace(" gl", " __gl") + '\n'
			gen_chr += TEMPLATE_CHR.replace("_RTN_TYPE", rtn_t) \
							.replace("_MILKO_FUNCTION_NAME", "milko_" + api) \
							.replace("_DO_FUNCTION_NAME", "Milko_Handle_" + handle_api_name) \
							.replace("_RETURN", "" if rtn_t == "void" else "return ") \
							.replace("_ARGS", ", ".join(android_names)) \
							.replace("_ARG_DEFS", ", ".join(args_def))
			chr_handle_signature = gl2_api[api]["signature"].replace(" {", ";")
			chr_handle_signature = \
				re.sub(r' gl.*?\(', ' Milko_Handle_' + handle_api_name + ' (', chr_handle_signature)
			chr_export += chr_handle_signature + '\n'

			success_api.append(api)
			success_handle_data[handle_api_name] = gl2_api[api]

			log_debug_no_text("%s  ->  %s%s\n", api, matches[0], \
				"\n\033[1;91mWarning: shim conflict\033[0m" if api.startswith("__") else "")

		else:
			log_warning_no_text("%s does not match%s\n", api, "" if api.startswith("__") else "")


	# generate handle (milko_helper), put these code right below the line 'include gles2_cmd_decoder_autogen.h'
	if (True):
		handle_set = handle(success_handle_data, \
			['/home/zephyr/milkomeda/chromium_android/src/gpu/command_buffer/service/gles2_cmd_decoder.cc',\
			'/home/zephyr/milkomeda/chromium_android/src/gpu/command_buffer/service/gles2_cmd_decoder_autogen.h'])
		functions = handle_set.get_all_handle()
		processed_functions = handle_set.process_all_function_body(functions)
		for name, body in processed_functions.iteritems():
			print body
			print '*'*30

	if (True):
		# print generated Android code
		print gen # append this to the end of gl.cpp
		print DIVIDER
		print gen_export # append this next to the func signatures in gl.cpp
		print DIVIDER
		# print chromium code
		print gen_chr # append this to the end of gles2_cmd_decoder.cc (within namespace gles2)
		print DIVIDER
		print chr_export # append this to the GLES2CmdDecoderImpl class's public declaration

	# write header file
	if (True):
		with open("/mnt/bullhead_milkomeda/frameworks/native/opengl/medalibs/GLES2/gl2_api.in") as fd:
			header=fd.read()
		for i in success_api:
			header = header.replace("API_ENTRY(" + i + ")", "API_ENTRY(__" + i + ")")
		with open("/mnt/bullhead_milkomeda/frameworks/native/opengl/medalibs/GLES2/gl2_api.in", "w") as fd:
			fd.write(header)

		replace_all_gl_name("/home/zephyr/milkomeda/chromium_android/src/gpu/command_buffer/service")

# some params type is parsed incorrectly
# e.g. const GLchar *const*string
# below are some fixes, just copy and replace these functions
""" ANDROID
void glShaderSource(GLuint shader, GLsizei count, const GLchar *const*string, const GLint *length) {
    LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    void (*checkedGL)(GLuint, GLsizei, const GLchar *const*, const GLint*) = reinterpret_cast<void(*)(GLuint, GLsizei, const GLchar *const*, const GLint*)>
      (dlsym(handle, "milko_glShaderSource"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else { checkedGL(shader, count, string, length); }
    LOGDBG1("%s: %s", __func__, "[1] success");
}

void glTransformFeedbackVaryings(GLuint program, GLsizei count, const GLchar *const*varyings, GLenum bufferMode) {
    LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    void (*checkedGL)(GLuint, GLsizei, const GLchar *const*, GLenum) = reinterpret_cast<void(*)(GLuint, GLsizei, const GLchar *const*, GLenum)>
      (dlsym(handle, "milko_glTransformFeedbackVaryings"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else { checkedGL(program, count, varyings, bufferMode); }
    LOGDBG1("%s: %s", __func__, "[1] success");
}

void glGetUniformIndices(GLuint program, GLsizei uniformCount, const GLchar *const*uniformNames, GLuint *uniformIndices) {
    LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    void (*checkedGL)(GLuint, GLsizei, const GLchar *const*, GLuint*) = reinterpret_cast<void(*)(GLuint, GLsizei, const GLchar *const*, GLuint*)>
      (dlsym(handle, "milko_glGetUniformIndices"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else { checkedGL(program, uniformCount, uniformNames, uniformIndices); }
    LOGDBG1("%s: %s", __func__, "[1] success");
}


void * glMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access) {
    LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    void * (*checkedGL)(GLenum, GLintptr, GLsizeiptr, GLbitfield) = reinterpret_cast<void *(*)(GLenum, GLintptr, GLsizeiptr, GLbitfield)>
      (dlsym(handle, "milko_glMapBufferRange"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else { return checkedGL(target, offset, length, access); }
    LOGDBG1("%s: %s", __func__, "[1] success");
}

void glGetVertexAttribPointerv(GLuint index, GLenum pname, void **pointer) {
	LOGDBG1("%s: %s", __func__, "[0] init");
    dlerror(); // clear dlerror
    void (*checkedGL)(GLuint, GLenum, void**) = reinterpret_cast<void(*)(GLuint, GLenum, void**)>
      (dlsym(handle, "milko_glGetVertexAttribPointerv"));
    if (!checkedGL) { LOGERR("%s: %s", __func__, dlerror()); exit(0); } 
    else { checkedGL(index, pname, pointer); }
	LOGDBG1("%s: %s", __func__, "[1] success");
}
"""

# Remove glGetString, glGetFloatv from all generated code

""" CHROMIUM
extern "C" __attribute__((visibility("default"))) void milko_glShaderSource(GLuint shader, GLsizei count, const GLchar *const*string, const GLint* length) {
  LOGDBG1("%s: [0]", __func__);
  milko_decoder_->Milko_Handle_ShaderSourceBucket(shader, count, string, length);
}

extern "C" __attribute__((visibility("default"))) void milko_glTransformFeedbackVaryings(GLuint program, GLsizei count, const GLchar *const*varyings, GLenum bufferMode) {
  LOGDBG1("%s: [0]", __func__);
  milko_decoder_->Milko_Handle_TransformFeedbackVaryingsBucket(program, count, varyings, bufferMode);
}

extern "C" __attribute__((visibility("default"))) void milko_glGetUniformIndices(GLuint program, GLsizei uniformCount, const GLchar *const*uniformNames, GLuint* uniformIndices) {
  LOGDBG1("%s: [0]", __func__);
  milko_decoder_->Milko_Handle_GetUniformIndices(program, uniformCount, uniformNames, uniformIndices);
}

extern "C" __attribute__((visibility("default"))) void * milko_glMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access) {
  LOGDBG1("%s: [0]", __func__);
  return milko_decoder_->Milko_Handle_MapBufferRange(target, offset, length, access);
}

extern "C" __attribute__((visibility("default"))) void milko_glGetVertexAttribPointerv(GLuint index, GLenum pname, void** pointer) {
  LOGDBG1("%s: [0]", __func__);
  milko_decoder_->Milko_Handle_GetVertexAttribPointerv(index, pname, pointer);
}
"""

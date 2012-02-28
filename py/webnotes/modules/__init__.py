# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

"""
	Utilities for using modules
"""
import webnotes

transfer_types = ['Role', 'Print Format','DocType','Page','DocType Mapper','GL Mapper','Search Criteria', 'Patch']

def scrub(txt):
	return txt.replace(' ','_').replace('-', '_').replace('/', '_').lower()

def scrub_dt_dn(dt, dn):
	"""
		Returns in lowercase and code friendly names of doctype and name for certain types
	"""
	ndt, ndn = dt, dn
	if dt.lower() in ('doctype', 'search criteria', 'page'):
		ndt, ndn = scrub(dt), scrub(dn)

	return ndt, ndn

def get_item_file(module, dt, dn):
	"""
		Returns the path of the item file
	"""
	import os
	ndt, ndn = scrub_dt_dn(dt, dn)

	return os.path.join(get_module_path(module), ndt, ndn, ndn + '.txt')
	
def get_item_timestamp(module, dt, dn):
	"""
		Return ths timestamp of the given item (if exists)
	"""
	from webnotes.utils import get_file_timestamp
	return get_file_timestamp(get_item_file(module, dt, dn))

			
def get_module_path(module):
	"""
		Returns path of the given module (imports it and reads it from __file__)
	"""
	return Module(module).get_path()

def get_doc_path(dt, dn, module=None):
	"""
		Return the path to a particular doc folder
	"""
	import os
	
	if not module:
		if dt=='Module Def': 
			module=dn
		else:
			module = webnotes.conn.get_value(dt, dn, 'module')

	ndt, ndn = scrub_dt_dn(dt, dn)

	return os.path.join(get_module_path(module), ndt, ndn)

def reload_doc(module, dt, dn):
	"""
		Sync a file from txt to module
		Alias for::
			Module(module).reload(dt, dn)
	"""
	Module(module).reload(dt, dn)

def export_doc(doctype, name):
	"""write out a doc"""
	from webnotes.modules.export_module import write_document_file
	import webnotes.model.doc
	module = webnotes.conn.get_value(doctype, name, 'module')
	doclist = [d.fields for d in webnotes.model.doc.get(doctype, name)]
	write_document_file(doclist, module)


class ModuleManager:
	"""
		Module manager class, used to run functions on all modules
	"""
	
	def get_all_modules(self):
		"""
			Return list of all modules
		"""
		import webnotes.defs
		from webnotes.modules.utils import listfolders

		if hasattr(webnotes.defs, 'modules_path'):
			return listfolders(webnotes.defs.modules_path, 1)


class Module:
	"""
		Represents a module in the framework, has classes for syncing files
	"""
	def __init__(self, name):
		self.name = name
		self.path = None
		self.sync_types = ['txt','sql']
		self.code_types = ['js','css','py','html','sql']
	
	def get_path(self):
		"""
			Returns path of the module (imports it and reads it from __file__)
		"""
		if not self.path:

			import webnotes.defs, os

			try:
				# by import
				exec ('import ' + scrub(self.name)) in locals()
				self.path = eval(scrub(self.name) + '.__file__')
				self.path = os.path.sep.join(self.path.split(os.path.sep)[:-1])
			except ImportError, e:
				# force
				self.path = os.path.join(webnotes.defs.modules_path, scrub(self.name))
				
 		return self.path				
	
	def get_doc_file(self, dt, dn, extn='.txt'):
		"""
			Return file of a doc
		"""
		dt, dn = scrub_dt_dn(dt, dn)
		return self.get_file(dt, dn, dn + extn)
		
	def get_file(self, *path):
		"""
			Returns ModuleFile object, in path specifiy the package name and file name
			For example::
				Module('accounts').get_file('doctype','account','account.txt')
		"""
		import os
		path = os.path.join(self.get_path(), os.path.join(*path))
		if path.endswith('.txt'):
			return TxtModuleFile(path)
		if path.endswith('.sql'):
			return SqlModuleFile(path)
		if path.endswith('.js'):
			return JsModuleFile(path)
		else:
			return ModuleFile(path)
	
	def reload(self, dt, dn):
		"""
			Sync the file to the db
		"""
		import os
		dt, dn = scrub_dt_dn(dt, dn)
		path = os.path.exists(os.path.join(self.get_path(), os.path.join(dt, dn, dn + '.txt')))
		if not path:
			webnotes.msgprint("%s not found" % path)
		else:
			self.get_file(dt, dn, dn + '.txt').sync(force=1)
		
	def sync_all_of_type(self, extn, verbose=0):
		"""
			Walk through all the files in the modules and sync all files of
			a particular type
		"""
		import os
		ret = []
		for walk_tuple in os.walk(self.get_path()):
			for f in walk_tuple[2]:
				if f.split('.')[-1] == extn:
					path = os.path.relpath(os.path.join(walk_tuple[0], f), self.get_path())
					self.get_file(path).sync()
					if verbose:
						print 'complete: ' + path

	def sync_all(self, verbose=0):
		"""
			Walk through all the files in the modules and sync all files
		"""
		import os
		self.sync_all_of_type('txt', verbose)
		self.sync_all_of_type('sql', verbose)
	
class ModuleFile:
	"""
		Module file class.
		
		Module files can be dynamically generated by specifying first line is "#!python"
		the output
	"""
	def __init__(self, path):
		self.path = path
		
	def load_content(self):
		"""
			returns file contents
		"""
		import os
		if os.path.exists(self.path):
			f = open(self.path,'r')
			self.content = f.read()
			f.close()
		else:
			self.content = ''

		return self.content
		
	def read(self, do_execute = None):
		"""
			Return the file content, if dynamic, execute it
		"""
		self.load_content()
		if do_execute and self.content.startswith('#!python'):
			from webnotes.model.code import execute
			self.content = execute(self.content)
			
		return self.content

		
class TxtModuleFile(ModuleFile):
	"""
		Class for .txt files, sync the doclist in the txt file into the database
	"""
	def __init__(self, path):
		ModuleFile.__init__(self, path)
	
	def sync(self, force=1):
		"""
			import the doclist if new
		"""
		from webnotes.model.utils import peval_doclist
		doclist = peval_doclist(self.read())
		if doclist:					
			from webnotes.utils.transfer import set_doc
			set_doc(doclist, 1, 1, 1)

			# since there is a new timestamp on the file, update timestamp in
			# the record
			webnotes.conn.sql("update `tab%s` set modified=now() where name=%s" \
				% (doclist[0]['doctype'], '%s'), doclist[0]['name'])
	
			
class SqlModuleFile(ModuleFile):
	def __init__(self, path):
		ModuleFile.__init__(self, path)
	
	def sync(self):
		"""
			execute the sql if new
			The caller must either commit or rollback an open transaction
		"""

		content = self.read()
		
		# execute everything but selects
		# theses are ddl statements, should either earlier
		# changes must be committed or rollbacked
		# by the caller
		if content.strip().split()[0].lower() in ('insert','update','delete','create','alter','drop'):
			webnotes.conn.sql(self.read())

		# start a new transaction, as we have to update
		# the timestamp table
		webnotes.conn.begin()
			
class JsModuleFile(ModuleFile):
	"""
		JS File. read method will read file and replace all $import() with relevant code
		Example::
			$import(accounts/common.js)
	"""
	def __init__(self, path):
		ModuleFile.__init__(self, path)
	
	def get_js(self, match):
		"""
			New style will expect file path or doctype
			
		"""
		name = match.group('name')
		custom = ''

		import webnotes.defs, os
		
		if os.path.sep in name:
			module = name.split(os.path.sep)[0]
			path = os.path.join(Module(module).get_path(), os.path.sep.join(name.split(os.path.sep)[1:]))
		else:
			# its a doctype
			path = os.path.join(get_doc_path('DocType', name), scrub(name) + '.js')
	
			# add custom script if present
			from webnotes.model.code import get_custom_script
			custom = get_custom_script(name, 'Client') or ''
			
		return JsModuleFile(path).read() + '\n' + custom
			
	def read(self):
		"""
			return js content (replace $imports if needed)
		"""
		self.load_content()
		code = self.content
		
		if code and code.strip():
			import re
			p = re.compile('\$import\( (?P<name> [^)]*) \)', re.VERBOSE)

			code = p.sub(self.get_js, code)
						
		return code

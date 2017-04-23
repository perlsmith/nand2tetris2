# started with VMtranslator since that one already does files/directory (somewhat)
# difference here is that you output multiple files
# File.jack --> FileT.xml
# tokenizer only outputs all tokens seen without recognizing any patterns - that's the
# syntax analyzer - FYI

keyword: 'class' I 'constructor' | 'function' | 'method' | 'field' | 'static'I
'var" | 'int' | 'char' | 'boolean' | 'void' | 'true' | 'false' I 'null' | 'this'l
'let' I 'do' | 'if' | 'else' | 'while' | 'return'


import sys
import re
import pdb	# to be able to use the debugger
import textwrap
import os 	# to check if a directory has been provided
import subprocess # to be able to get files using *.vm

class Parser():
	def __init__( self, filename ):
		self.instream = open( filename, "r")	# be nice to do some exception handling :)
		# need to support directories - pending..
		match = re.match( "^.+?([^\\/]+)\.vm" , filename )		# dir1\dir2\name.vm --> name is what we capture
		self.base = match.group(1)
		
	def hasMoreCommands( self ):
		self.nextline = self.instream.readline();
		if not self.nextline:
			return False
		else:
			self.command = self.nextline.split()
			if ( 0 == len( self.command) or '//' == self.command[0] ):
				return self.hasMoreCommands()
			else:
				return True
			
	def advance( self ):
		self.instr = self.command[0]
		if len( self.command ) > 1 :
			self.args1 = self.command[1]
			if len( self.command ) > 2 :
				self.args2 = self.command[2]
			
	

		

# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/File1T.xml - for each..

# if no files in the specified source, then die..

source = sys.argv[1]
# pdb.set_trace()	
	
if os.path.isdir( source ) :
	# start off writing to source/source.asm by processing every .vm file you encounter
	filelist = os.popen( "ls " + source + "/*.jack").read().split()
	if len( filelist ) < 1 :
		print( "Please check if the directory has .jack files in it" )
else :
	if re.match( "\./jack" , source ) :
		filelist = [source]
	else :
		print( "Only operates on .jack files" )
		sys.exit()

vm_codewr = CodeWriter( target )


for file in filelist :
	vm_parser = Parser( file )
	target = re.sub( "\.jack" , "T.xml" , file )

	while vm_parser.hasMoreCommands():
		vm_parser.advance()
#		print( vm_parser.instr)

		






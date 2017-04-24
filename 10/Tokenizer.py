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
		self.buffer = ''
		
	def hasMoreAtoms( self ):
		if ( '' == self.nextline ) :
			self.nextline = self.instream.readline();
		else : 		# there are tokens to process
			return True
			
		if not self.nextline:
			return False
		else:
			return True
			
	def advance( self ):	# will only be called when nextline is not ''
		atom = self.buffer[0]
		self.buffer = self.buffer[1:]
		return atom
			
	
class TknWriter() :
	# also implements the translation for <,>, & --> &lt; &gt; &amp;
	specials = {'<' : r"&lt;" , '>' : r"&gt;" , '&' : r"&amp;" }
	
	def __init__( self, outfile ):
		self.outstream = open( outfile, "w" )
		self.outstream.write( r"<)
		
	def writeToken( self, type, value ) :
		

	def Close( self ) :
		
		
# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/File1T.xml - for each..

# if no files in the specified source, then die..

source = sys.argv[1]
# pdb.set_trace()	

state = 'START';
buffer = '';

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



for file in filelist :
	j_parser = Parser( file )
	target = re.sub( "\.jack" , "T.xml" , file )
	j_TknWriter = TknWriter( target )

	while j_parser.hasMoreCommands():
		atom = j_parser.advance()
		if ( 'START' == state ) :
			if ( re.match( r"\d" ) , atom ) :
				state = "INTCONST"
				buffer = atom
			elif ( re.match( r"[_a-zA-Z]" , atom ) ) :
				state = "WORD"
				buffer = atom
			elif ( re.match( r"[{}().,;+-\[\]/&|<>=~]|\*" , atom ) ) :
				j_TknWriter.writeToken( "SYM" , atom )
			elif ( re.match( '"') , atom ) :
				state = "STRCONST"
		elif ( 'WORD' == state ) :
			if ( re.match( r"_[0-9a-zA-Z]" ) , atom ) :
				buffer = buffer + atom
			elif ( re.match( r"[{}().,;+-\[\]/&|<>=~]|\*" , atom ) ) :
				j_TknWriter.writeToken( "WORD" , buffer )
				j_TknWriter.writeToken( "SYM" , atom )
			else :


		






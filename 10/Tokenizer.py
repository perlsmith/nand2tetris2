# started with VMtranslator since that one already does files/directory (somewhat)
# difference here is that you output multiple files
# File.jack --> FileT.xml
# tokenizer only outputs all tokens seen without recognizing any patterns - that's the
# syntax analyzer - FYI
# this is "phase 1 " :) For phase 2, we need a way to code the rules elegantly. The
# proposed method of having a function for each statement type doesn't seem elegant..
# currently no support for double-quote - maybe need to add detection of escaped (\") double quote?


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
		self.nextline = ''
		self.mode = 'normal'		# to handle block comments - the tough guys :)

# handling comments is the hard part
#  ..... */   ..... /* -- if you were in comment mode, then you have to stay in comment mode :)
		
	def hasMoreAtoms( self ):
		if ( '' == self.nextline ) :
			self.nextline = self.instream.readline();
			# pdb.set_trace()
			if( 'normal' == self.mode ) :
				self.nextline = re.sub( r"/\*.+?\*/" , '' , self.nextline ) # in a non-greedy way, swallow up all comments
				# only allowed to do this in normal mode - if you were already in comment mode, you'd have to eat up everything
				# till */ :)
				if( re.search( r"/\*" , self.nextline ) ) :	# something escaped the earlier lunch..
					self.mode = "comment"
					self.nextline = re.sub ( r"/\*.+" , '' , self.nextline )
			elif( 'comment' == self.mode ) :
				if ( re.search( r"\*/" , self.nextline ) ) :
					self.mode = 'normal'
				else :
					self.nextline = "\n"	# swallow all because you haven't seen a block cmt terminator
				self.nextline = re.sub( r"^.+?\*/" , '' , self.nextline )	# now, swallow up all till the first(!) terminator
				self.nextline = re.sub( r"/\*.+?\*/" , '' , self.nextline ) # in a non-greedy way, swallow up all comments
				if( re.search( r"/\*" , self.nextline ) ) :	# something escaped the earlier lunch..
					self.mode = "comment"
					self.nextline = re.sub ( r"/\*.+" , '' , self.nextline )				
			self.nextline = re.sub( r"//.+$" , "" , self.nextline )	# get rid of inline comments
		else : 		# there are tokens to process
			return True
			
		if not self.nextline:
			return False
		else:
			return True
			
	def advance( self ):	# will only be called when nextline is not ''
		atom = self.nextline[0]		# that is, the first character of the string
		self.nextline = self.nextline[1:]	# the remainder of the string
		return atom
			
	
class TknWriter() :
	# also implements the translation for <,>, & --> &lt; &gt; &amp;
	specials = {'<' : r"&lt;" , '>' : r"&gt;" , '&' : r"&amp;" }
	keywds = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return']

	
	def __init__( self, outfile ):
		self.outstream = open( outfile, "w" )
		self.outstream.write( "<tokens>\n")
		
	def writeToken( self, type, value ) :	# WORD, stringConstant, SYM, integerConstant and WORD will generate identifier or keyword..
		if( "WORD" == type ) :
			if( value in self.keywds ) :
				self.outstream.write( "" + '<keyword> ' + value + " </keyword>\n" )
			else :
				self.outstream.write( "" + '<identifier> ' + value + " </identifier>\n" )
		elif ( "SYM" == type ) :
			if( value in self.specials.keys() ) :
				value = self.specials[value]
			self.outstream.write( "" + '<symbol> ' + value + " </symbol>\n" )
		else :
			self.outstream.write( "" + '<' + type + '> ' + value + ' </' + type + ">\n" )
		

	def Close( self ) :
		self.outstream.write( "</tokens>\n")
		self.outstream.close()
		
# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/File1Tokens.xml - for each..

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
	if re.search( r"\.jack" , source ) :
		filelist = [source]
	else :
		print( "Only operates on .jack files" )
		sys.exit()



for file in filelist :
	j_parser = Parser( file )
	target = re.sub( "\.jack" , "Tokens.xml" , file )
	j_TknWriter = TknWriter( target )

	while j_parser.hasMoreAtoms():		# == as long as the string that began as the line read from file minus comments is not ''
		atom = j_parser.advance()
		if ( 'START' == state ) :
			buffer = ''
			if ( re.match( r"\d"  , atom )  ):
				state = "INTCONST"
				buffer = atom
			elif ( re.match( r"[_a-zA-Z]" , atom ) ) :
				state = "WORD"
				buffer = atom
			elif ( re.match( r"[{}().,;+-\[\]/&|<>=~]|\*" , atom ) ) :
				j_TknWriter.writeToken( "SYM" , atom )
			elif ( '"' ==  atom ) :
				state = "STRCONST"
		elif ( 'WORD' == state ) :
			if ( re.match( r"[_0-9a-zA-Z]" , atom ) ) :
				buffer = buffer + atom
			elif ( re.match( r"[{}().,;+-\[\]/&|<>=~]|\*" , atom ) ) :
				j_TknWriter.writeToken( "WORD" , buffer )
				j_TknWriter.writeToken( "SYM" , atom )
				state = 'START'
			else :
				j_TknWriter.writeToken( "WORD" , buffer )
				state = 'START'
		elif ( 'INTCONST' == state ) :
			if ( re.match( r"\d"  , atom ) ) :
				state = "INTCONST"
				buffer = buffer + atom
			elif( re.match( r"[{}().,;+-\[\]/&|<>=~]|\*" , atom ) ) :
				j_TknWriter.writeToken( "integerConstant" , buffer )
				j_TknWriter.writeToken( "SYM" , atom )
				state = 'START'
			else :
				j_TknWriter.writeToken( "integerConstant" , buffer )
				state = 'START'
		elif ( 'STRCONST' == state ) :
			if ( '"' == atom ) :
				state = 'START'
				j_TknWriter.writeToken( "stringConstant" , buffer )
			else :
				buffer = buffer + atom

				
	j_TknWriter.Close();

		






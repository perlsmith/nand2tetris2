# started with Tokenizer.. since that one does files/directories correctly.. might
# need a shell wrapper to stitch both together - need to see how easy that is in Py
# this one does the pattern recognition..

# here's how :
# when Shimon says :

# class : 'class className '{' classVarDec* subroutineDec* '}'
# we code :
# rules = {}
# rules['class'] = 'class$1$-className$1${$1$-classVarDec$*$-subroutineDec$*$}$1'
# parse that using split($) to get the rule
# while analyzing, you "look for" what the rule specifies and eat accordingly.
# when you expect x and don't get it, you just exit.. very primitive analyzer..
# what you're looking for is based on state - you may already be in a rule..
# if not, you loop through all rules..
# actually, you do start off looking for a class. One per file.. that's dictated by program
# structure..


import sys
import re
import pdb	# to be able to use the debugger
import textwrap
import os 	# to check if a directory has been provided
import subprocess # to be able to get files using *.vm

class Analyzer():
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
					self.nextline = "\n"	# swallow all
				self.nextline = re.sub( r"^.+?\*/" , '' , self.nextline )	# now, swallow up all till the first(!) terminator
				self.nextline = re.sub( r"/\*.+?\*/" , '' , self.nextline ) # in a non-greedy way, swallow up all comments
				if( re.search( r"/\*" , self.nextline ) ) :	# something escaped the earlier lunch..
					self.mode = "comment"
					self.nextline = re.sub ( r"/\*.+" , '' , self.nextline )				
			self.nextline = re.sub( r"//.+$" , "" , self.nextline )
		else : 		# there are tokens to process
			return True
			
		if not self.nextline:
			return False
		else:
			return True
			
	def advance( self ):	# will only be called when nextline is not ''
		atom = self.nextline[0]
		self.nextline = self.nextline[1:]
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
		
# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/File1T.xml - for each..

# if no files in the specified source, then die..

source = sys.argv[1]
# pdb.set_trace()	

state = 'START';
buffer = '';

if os.path.isdir( source ) :
	# start off writing to source/fileAnalyzed.xml by processing every *Tokens.xml file you encounter
	filelist = os.popen( "ls " + source + "/*Tokens.xml").read().split()
	if len( filelist ) < 1 :
		print( "Please check if the directory has *Tokens.xml files in it (Eg. SquareTokens.xml" )
else :
	if re.search( r"\Tokens.xml" , source ) :
		filelist = [source]
	else :
		print( "Only operates on *Tokens.xml files" )
		sys.exit()



for file in filelist :
	j_parser = Parser( file )
	target = re.sub( "Tokens\.xml" , "Analyzed.xml" , file )
	j_TknWriter = TknWriter( target )

	while j_parser.hasMoreAtoms():


		






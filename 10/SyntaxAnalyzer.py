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
# per the lecture - if you see a non-terminal construct, you end up with another look-for cycle (or a call to a routine as Shimon says)
# for now, we're going to assume the Tokenizer has been run and we operate on the fileTokens.xml output
# later, we'll combine into a single program

# how should the execution be architected in an OO way? one class - with a get token method and a write 
# token method.. and a check token method and a get rule method.. you start off looking for a class declaration..

# since expression parsing is L2, when you're checking expressions you'll have to eat an additional token into the buffer


import sys
import re
import pdb	# to be able to use the debugger
import textwrap
import os 	# to check if a directory has been provided
import subprocess # to be able to get files using *.xml

class Analyzer():
	rules = {}
	elements = {}
	# note : 1 => 1, 2 => 0 or 1 (?) , 3 => 0 or more (*)
	rules['class'] = ['class' , 1, 'className' , 1, '{' , 1, ,  'classVarDec' , 3, 'subroutineDec' , 3 , '}' , 1 ]
	elements['class'] = ['keyword', 'identifier' , 'symbol', 'rule' , 'rule' , 'symbol' ]
	rules['classVarDec'] = ['static|field' , 1 , 'type' , 1 , 'varName' , 1 , '_addlVarDec', 3  , ';' , 1 ]
	elements['classVarDec'] = ['keyword' , 'rule' , 'identifier' , 'rule']
	rules['_addlVarDec'] = [',' , 1, 'varName', 1 ]		# _name implies this rule will not generate a token
	elements['_addlVarDec'] = ['symbol', 'identifier']
	rules['type'] = ['int|char|boolean||className' , 1]
	elements['type'] = ['keyword||identifier']
	rules['subroutineDec'] = ['constructor|function|method' , 1 , 'void||type' , 1 , 'subroutineName' , 1 , '(', 1, 'parameterList' , 1 , ')' , 'subroutineBody' , 1]
	elements['subroutineDec'] = ['keyword' , 'keyword||rule' , 'identifier' , 'symbol' , 'rule', 'symbol', 'rule' ]
	# what this means is that you first look for keyword : void - if you see void, then your put down <keyword> void </keyword> else
	# you look at type - which is again looking for keyword : int|char|boolean .... you get the idea..
	
	rules['parameterList'] = [ '_params' , 2 ]
	elements[parameterList'] = ['rule']
	rules['_params'] = [ '_param' , 1 , '_addlParam' , 3 ]
	elements['_params'] = ['rule' , 'rule' ]
	rules['_param'] = ['type' , 1, 'varName' , 1 ]
	elements['_param'] = ['rule', 'identifier']
	rules['_addlParam' ] = [ ',' , 1 , 'varName' , 1]
	elements['_addlParam' ] = [ 'symbol' , 'identifier' ]
	rules['subroutineBody'] = ['{' , 1 , 'varDec' , 3 , 'statements' , 1 , '}' , 1 ]
	elements['subroutineBody'] = ['symbol' , 'rule', 'rule', 'symbol' ]
	rules['varDec'] = ['var' , 1, 'type' , 1, 'varName' , '_addlVarDec' , 3 , ';' , 1 ]
	elements['varDec'] = ['keyword' , 'rule' , 'identifier' , 'rule' , 'symbol' ]
	rules['statements'] = ['_statement' , 3 ]	# this was a curve ball - didn't realize they don't want <statement> ha!
	elements['statements'] = ['rule']
	rules['_statement'] = ['letStatement|ifStatement|whileStatement|doStatement|returnStatement']
	elements['_statement'] = ['rule']
	rules['letStatement'] = ['let' , 1 , 'varName' , 1 , '_index' , 2 , '=' , 1 , 'expression' , 1 , ';' , 1 ]
	elements['letStatement'] = ['keyword' , 'identifier', 'rule' , 'symbol' , 'rule', 'symbol' ]
	rules['_index'] = ['[' , 1 , 'expression' , 1 , ']' , 1 ]
	elements['_index'] = [ 'symbol' , 'rule' , 'symbol' ]
	rules['ifStatement'] = ['if' , 1 , '(' , 1 , 'expression' , 1 , ')' , '{' , 1 , 'statements' , '}' , 1 , '_elseBlock' , 2 ]
	elements['ifStatement'] = ['keyword' , 'symbol', 'rule', 'symbol', 'symbol', 'rulel , 'symbol' , 'rule' ]
	rules['_elseBlock' ] = ['else' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 ]
	elements['_elseBlock' ] = [ 'keyword', 'symbol', 'rule' , 'symbol' ]
	rules['whileStatement'] = ['while', 1 , '(' , 'expression' , 1 , ')' , '{' , 1 , 'statements' , 1 , '}' , 1 ]
	elements['whileStatement'] = ['keyword' , 'symbol' , 'rule', 'symbol' , 'symbol' , 'rule' , 'symbol' ]
	rules['doStatement'] = ['do' , 1 , 'subroutineCall' , 1 , ';' , 1 ]
	elements['doStatement'] = ['keyword' , 'rule' , 'symbol' ]
	rules['returnStatement'] = ['return' , 1 , 'expression' , 2 , ';' , 1 ]
	elements['returnStatement'] = ['keyword' , 'rule' , 'symbol' ]
	rules['expression'] = ['term' , 1 , '_subExp' , 3 ]
	elements['expression'] = ['rule' , 'rule' ]
	rules['_subExp'] = ['op' , 1 , 'term' , 1 ]
	elements['_subExp'] = ['+,-,*,/,&,|,<,>,=' , 'rule']	# special case - CSV - the rule-entry - in this case op will go out as <op> CSV-item </op>
	rules['term'] = ['integerConstant|stringConstant|keywordConstant||varName|_arrayElem|subroutineCall|_paranthExp|_unOpTerm]
	elements['term'] = ['literal||rule']	# literal is special - you just look for what is in the rules[] and print that as the token name..
	rules['_arrayElem'] = ['varName' , 1 , '[' , 1 , 'expression' , 1 , ']' , 1 ]
	elements['_arrayElem'] = ['rule' , 'symbol', 'rule' , 'symbol' ]
	rules['_paranthExp'] = ['(' , 1 , 'expression' , 1, ')' ]
	elements['_paranthExp'] = ['symbol' , 'rule' , 'symbol' ]
	rules['_unOpTerm' ] = ['unaryOp' , 1 , 'term' , 1 ]
	elements['_unOpTerm' ] = ['-,~', 'rule']	# this is another special case - a CSV -- you put the rule-entry - in this case, <unaryOp>
	rules['subroutineCall'] = [ '_simpleCall|_classMethCall' , 1 ]
	elements['subroutineCall'] = [ 'rule' ]
	rules['_simpleCall' ] = [ 'subroutineName' , 1 , '(' , 1 , 'expressionList' , 1 , ')' , 1 ]
	elements['_simpleCall' ] = [ 'identifier' , 'symbol' , 'rule' , 'symbol' ]
	rules['_classMethCall' ] = [ 'varName' , 1 , '.', 1 , 'subroutineName' , 1 , '(' , 'expressionList' , 1 , ')' , 1 ]
	elements['_classMethCall' ] = [ 'identifier' , 'symbol' , 'identifier' , 'symbol' , 'rule' , 'symbol' ]
	rules['expressionList' ] = [ '_expressions' , 2 ] 
	elements['expressionList'] = [ 'rule']
	rules['_expressions'] = [ 'expression' , 1 , '_addlExpr' , 3 ]
	elements['_expressions'] = ['rule' , 'rule']
	rules['_addlExpr'] = [',' , 1 , 'expression' , 1 ]
	elements['_addlExpr'] = ['symbol' , 'rule']
	rules['keywordConstant' ] = ['true|false|'null'|'this']
	elements['keywordConstant'] = ['literal']
	
	
	
	

	def __init__( self, filename ):
		self.instream = open( filename, "r")	# be nice to do some exception handling :)
		# need to support directories - pending..
		self.nextline = ''

		
	def hasMoreAtoms( self ):
		if ( '' == self.nextline ) :
			self.nextline = self.instream.readline()
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


		






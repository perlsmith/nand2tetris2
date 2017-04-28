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
	rules = {}		# tells you what to look for
	elements = {}	# tells you what tag you're going to write to the output..
	# note : 1 => 1, 2 => 0 or 1 (?) , 3 => 0 or more (*)
	rules['class'] = ['class' , 1, 'className' , 1, '{' , 1 ,  'classVarDec' , 3, 'subroutineDec' , 3 , '}' , 1 ]
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
	elements['parameterList'] = ['rule']
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
	elements['ifStatement'] = ['keyword' , 'symbol', 'rule', 'symbol', 'symbol', 'rule' , 'symbol' , 'rule' ]
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
	rules['_subExp'] = ['[+-*/&|<>]=' , 1 , 'term' , 1 ]	# intended for us in a regex search -- 
	elements['_subExp'] = ['symbol' , 'rule']	# special case - CSV - the rule-entry - in this case op will go out as <op> CSV-item </op>
	rules['term'] = ['integerConstant|stringConstant|keywordConstant||varName|_arrayElem|subroutineCall|_paranthExp|_unOpTerm' , 1]
	elements['term'] = ['literal||rule']	# literal is special - you just look for what is in the rules[] and print that as the token name..
	rules['_arrayElem'] = ['varName' , 1 , '[' , 1 , 'expression' , 1 , ']' , 1 ]
	elements['_arrayElem'] = ['rule' , 'symbol', 'rule' , 'symbol' ]
	rules['_paranthExp'] = ['(' , 1 , 'expression' , 1, ')' ]
	elements['_paranthExp'] = ['symbol' , 'rule' , 'symbol' ]
	rules['_unOpTerm' ] = ['[-~]' , 1 , 'term' , 1 ]
	elements['_unOpTerm' ] = ['symbol', 'rule']	# this is another special case - a CSV -- you put the rule-entry - in this case, <unaryOp>
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
	rules['keywordConstant' ] = ['true|false|null|this']
	elements['keywordConstant'] = ['literal']
	# op and unaryOp were also curve balls - be clear - say that those will not generate tokens!!
	

	def __init__( self, filename ):
		self.instream = open( filename, "r")	# be nice to do some exception handling :)
		target = re.sub( "Tokens\.xml" , "Analyzed.xml" , filename )
		self.outstream = open( target, "w" )
		self.nextline = ''
		self.lineN = 1

	def Write( self, buffer ) :		# buffer could be very big - so might need a better way to deal with this
		self.outstream.write( buffer )
		self.outstream.close()
		
		
	# this is the main operator that uses other methods - maybe an OO noob style deprecated, but..	
	# elements[xyz][] -- if you see 'rule' that results in another call to analyze()
	#					-- if you see || then you split on || and process the resulting list in OR fashion - first one that hits terminates
	#					-- if you see 'literal' then you look for tokenName matching what rules[][] specifies
	# open question at this point - how do you know if you should terminate with an error or if you
	# are in a ? or * so you just move on to the next thing? You need a token buffer where you store
	# stuff so you can backtrack - when you're in a ? or * - so the next rule can use what you've read in so far.. :)
	# you only want to issue an error when you MUST see something - if you're within a ? or *, you can't ERROR out :)
	def analyze( self, ruleName, priority ) :		# priority is the same as 1,2,3 for 1, ?, *
		#pdb.set_trace()
		# will call itself recursively when it uses self.rules[] to process the input rule..
		# get a token, see if it fits, move on.
		buffer = ''
		rule = self.rules[ruleName]
		whatIs = self.elements[ruleName]
		numR = len( rule ) >> 1
		for i in range( numR ) :
			seekToken = rule[2*i]
			count = rule[2*i + 1]	# 1 => 1; 2 => ? ; 3 => *
			# symbol can't be combined with anything else in an OR.. so check for that first.
			if ('symbol' == whatIs[i] ) :
				# use seekToken as a regex
				if ( not self.hasMoreTokens() ) :
					print( "Prematurely out of tokens.." )
					sys.exit()
				if( re.match( seekToken , self.token ) ) :
					buffer = buffer + self.nextline
				else :
					if( 1 == priority ) :
						print( "Line num : " + str(self.lineN) + ", expecting : " + seekToken + " but got\n" + self.token )
					return ''
			else :
				types = whatIs[i].split('||')
				
			
		return buffer
			# in the case of 2 or 3, you only add whatIs if you actually find the patterns..
		
		

		
	def hasMoreTokens( self ):
		self.nextline = self.instream.readline();
		self.lineN = self.lineN + 1
		if not self.nextline:
			return False
		else:
			if( re.match( '<tokens>' , self.nextline ) ) :
				self.nextline = self.instream.readline()
			match = re.match( "^\s*<(\S+)>\s*(\S+)" , self.nextline )
			if( match ) :
				self.tokenName = match.group(1)
				self.token = match.group(2)
				re.sub( r"&lt;" , "<" , self.token )
				re.sub( r"&gt;" , ">" , self.token )
				re.sub( r"&amp;" , "&" , self.token )
			else :
				print( "Unsupported line in input file" )
				sys.exit()
			return True
			
			

			
# Main program :

# if a directory "Adder" is input containing .jack files, then the output is Adder/File1.xml - for each..

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
	j_analyzer = Analyzer( file )	# this does an init and also open the target for writing..
#	j_analyzer.Write( j_analyzer.analyze('class') )	# will also write
	print( j_analyzer.analyze('_unOpTerm' , 1) )
	print( j_analyzer.analyze('_unOpTerm' , 1) )


		






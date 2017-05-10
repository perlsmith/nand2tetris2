# refer older versions for older comments 

# implements LL2 for expression. Uses a priority level when checking the token to decide if there's an error in input code

# Shimon's suggestion was to use a unique method for every higher-level construct
# we're implementing differently here
# we code all the rules in a way that the analyzer can access easily
# there is one core analyzer function that calls itself each time it encounters a new rule (while processing current rule)
# elements : have to deal with || , type of token (simple or rule)
# rules : if the name starts with _ then we don't emit a new token ( such as _additionalParameterDeclaration )
# if what elements specifies matches what the <tokenType> says, then also you don't emit a new token.. Eg. keyword..

# this implementation style has basically created a new language that can be used to define a language..
# so, we could use this to easily build a compiler for a new language - only, it has to be LL2 for expressions and LL1 
# everywhere else..

import sys
import re
import pdb	# to be able to use the debugger
import textwrap
import os 	# to check if a directory has been provided
import subprocess # to be able to get files using *.xml

class Analyzer():

	# the only motivation for this is to be able to fold and manage the code easily :)
	# wasn't going to work on this today, but, saw Gregor Kickzales tip on doing a bit everyday :)
	def encode_lingo( self) :
		self.rules = {}		# tells you what to look for
		self.elements = {}	# tells you what tag you're going to write to the output..
		# note : 1 => 1, 2 => 0 or 1 (?) , 3 => 0 or more (*)
		self.rules['class'] = ['class' , 1, 'className' , 1, '{' , 1 ,  'classVarDec' , 3, 'subroutineDec' , 3 , '}' , 1 ]
		self.elements['class'] = ['keyword', 'identifier' , 'symbol', 'rule' , 'rule' , 'symbol' ]
		self.rules['classVarDec'] = ['static|field' , 1 , 'type' , 1 , 'varName' , 1 , '_addlVarDec', 3  , ';' , 1 ]
		self.elements['classVarDec'] = ['keyword' , 'rule' , 'identifier' , 'rule', 'symbol']
		self.rules['_addlVarDec'] = [',' , 1, 'varName', 1 ]		# _name implies this rule will not generate a token
		self.elements['_addlVarDec'] = ['symbol', 'identifier']
		self.rules['type'] = ['int|char|boolean||className' , 1]
		self.elements['type'] = ['keyword||identifier']
		self.rules['subroutineDec'] = ['constructor|function|method' , 1 , 'void||type' , 1 , 'subroutineName' , 1 , '(', 1, 'parameterList' , 1 , ')' , 1, 'subroutineBody' , 1]
		self.elements['subroutineDec'] = ['keyword' , 'keyword||rule' , 'identifier' , 'symbol' , 'rule', 'symbol', 'rule' ]
		# what this means is that you first look for keyword : void - if you see void, then your put down <keyword> void </keyword> else
		# you look at type - which is again looking for keyword : int|char|boolean .... you get the idea..
		
		self.rules['parameterList'] = [ '_params' , 2 ]
		self.elements['parameterList'] = ['rule']
		self.rules['_params'] = [ '_param' , 1 , '_addlParam' , 3 ]
		self.elements['_params'] = ['rule' , 'rule' ]
		self.rules['_param'] = ['type' , 1, 'varName' , 1 ]
		self.elements['_param'] = ['rule', 'identifier']
		self.rules['_addlParam' ] = [ ',' , 1 , 'varName' , 1]
		self.elements['_addlParam' ] = [ 'symbol' , 'identifier' ]
		self.rules['subroutineBody'] = ['{' , 1 , 'varDec' , 3 , 'statements' , 1 , '}' , 1 ]
		self.elements['subroutineBody'] = ['symbol' , 'rule', 'rule', 'symbol' ]
		self.rules['varDec'] = ['var' , 1, 'type' , 1, 'varName' , 1 , '_addlVarDec' , 3 , ';' , 1 ]
		self.elements['varDec'] = ['keyword' , 'rule' , 'identifier' , 'rule' , 'symbol' ]
		self.rules['statements'] = ['_statement' , 3 ]	# this was a curve ball - didn't realize they don't want <statement> ha!
		self.elements['statements'] = ['rule']
		self.rules['_statement'] = ['letStatement|ifStatement|whileStatement|doStatement|returnStatement', 1]
		self.elements['_statement'] = ['rule']
		self.rules['letStatement'] = ['let' , 1 , 'varName' , 1 , '_index' , 2 , '=' , 1 , 'expression' , 1 , ';' , 1 ]
		self.elements['letStatement'] = ['keyword' , 'identifier', 'rule' , 'symbol' , 'rule', 'symbol' ]
		self.rules['_index'] = ['[' , 1 , 'expression' , 1 , ']' , 1 ]
		self.elements['_index'] = [ 'symbol' , 'rule' , 'symbol' ]
		self.rules['ifStatement'] = ['if' , 1 , '(' , 1 , 'expression' , 1 , ')' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 , '_elseBlock' , 2 ]
		self.elements['ifStatement'] = ['keyword' , 'symbol', 'rule', 'symbol', 'symbol', 'rule' , 'symbol' , 'rule' ]
		self.rules['_elseBlock' ] = ['else' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 ]
		self.elements['_elseBlock' ] = [ 'keyword', 'symbol', 'rule' , 'symbol' ]
		self.rules['whileStatement'] = ['while', 1 , '(' , 'expression' , 1 , ')' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 ]
		self.elements['whileStatement'] = ['keyword' , 'symbol' , 'rule', 'symbol' , 'symbol' , 'rule' , 'symbol' ]
		self.rules['doStatement'] = ['do' , 1 , 'subroutineCall' , 1 , ';' , 1 ]
		self.elements['doStatement'] = ['keyword' , 'rule' , 'symbol' ]
		self.rules['returnStatement'] = ['return' , 1 , 'expression' , 2 , ';' , 1 ]
		self.elements['returnStatement'] = ['keyword' , 'rule' , 'symbol' ]
		self.rules['expression'] = ['term' , 1 , '_subExp' , 3 ]
		self.elements['expression'] = ['rule' , 'rule' ]
		self.rules['_subExp'] = ['[+-*/&|<>]=' , 1 , 'term' , 1 ]	# intended for us in a regex search -- 
		self.elements['_subExp'] = ['symbol' , 'rule']	# special case - CSV - the rule-entry - in this case op will go out as <op> CSV-item </op>
		self.rules['term'] = ['integerConstant|stringConstant|_keywordConstant|varName|_arrayElem|subroutineCall|_paranthExp|_unOpTerm' , 1]
		self.elements['term'] = ['rule']	# literal is special - you just look for what is in the rules[] and print that as the token name..
		self.rules['_constant'] = ['*||*' , 1]
		self.elements['_constant'] = ['integerConstant||stringConstant']
		self.rules['_arrayElem'] = ['varName' , 1 , '[' , 1 , 'expression' , 1 , ']' , 1 ]
		self.elements['_arrayElem'] = ['rule' , 'symbol', 'rule' , 'symbol' ]
		self.rules['_paranthExp'] = ['(' , 1 , 'expression' , 1, ')' ]
		self.elements['_paranthExp'] = ['symbol' , 'rule' , 'symbol' ]
		self.rules['_unOpTerm' ] = ['[-~]' , 1 , 'term' , 1 ]
		self.elements['_unOpTerm' ] = ['symbol', 'rule']	# this is another special case - a CSV -- you put the rule-entry - in this case, <unaryOp>
		self.rules['subroutineCall'] = [ '_simpleCall|_classMethCall' , 1 ]
		self.elements['subroutineCall'] = [ 'rule' ]
		self.rules['_simpleCall' ] = [ 'subroutineName' , 1 , '(' , 1 , 'expressionList' , 1 , ')' , 1 ]
		self.elements['_simpleCall' ] = [ 'identifier' , 'symbol' , 'rule' , 'symbol' ]
		self.rules['_classMethCall' ] = [ 'varName' , 1 , '.', 1 , 'subroutineName' , 1 , '(' , 1, 'expressionList' , 1 , ')' , 1 ]
		self.elements['_classMethCall' ] = [ 'identifier' , 'symbol' , 'identifier' , 'symbol' , 'rule' , 'symbol' ]
		self.rules['expressionList' ] = [ '_expressions' , 2 ] 
		self.elements['expressionList'] = [ 'rule']
		self.rules['_expressions'] = [ 'expression' , 1 , '_addlExpr' , 3 ]
		self.elements['_expressions'] = ['rule' , 'rule']
		self.rules['_addlExpr'] = [',' , 1 , 'expression' , 1 ]
		self.elements['_addlExpr'] = ['symbol' , 'rule']
		self.rules['_keywordConstant' ] = ['true|false|null|this']
		self.elements['_keywordConstant'] = ['keyword']
		# op and unaryOp were also curve balls - be clear - say that those will not generate tokens!!

	def __init__( self, filename ):
		self.instream = open( filename, "r")	# be nice to do some exception handling :)
		target = re.sub( "Tokens\.xml" , "Analyzed.xml" , filename )
		self.outstream = open( target, "w" )
		self.nextline = ''
		self.tokenStack = ''		# this enables backtracking - you have a token you read, now you have to 
									# stop processing this rule and process another one - so you have to
									# reuse the existing token
		self.lineN = 1
		self.encode_lingo()

	def Write( self, buffer ) :		# buffer could be very big - so might need a better way to deal with this
		self.outstream.write( buffer )
		self.outstream.close()
		
	# this is the main operator that uses other methods - maybe an OO noob style deprecated, but..	
	# elements[xyz][] -- if you see 'rule', that results in another call to analyze()
	#					-- if you see || then you split on || and process the resulting list in OR fashion - first one that hits terminates
	# open question at this point - how do you know if you should terminate with an error or if you
	# are in a ? or * so you just move on to the next thing? You need a token buffer where you store
	# stuff so you can backtrack - when you're in a ? or * - so the next rule can use what you've read in so far.. :) -- the LL2 helps out
	# you only want to issue an error when you MUST see something - if you're within a ? or *, you can't ERROR out :)
	# we'll have to update so that we have a single register token stack.. we first look there before
	# reading a new token from the file..
	# also, hunger can only get elevated when traversing a rule laterally -- going by LL1..
	def analyze( self, ruleName, hunger, severe=False ) :		# hunger is the same as 1,2,3 for 1, ?, *
		# returns a buffer containing tokens satisfying rule, or ''. If return is '', then 
		# decide if input is bad based on hunger and depth
		# pdb.set_trace()
		# will call itself recursively when it uses self.rules[] to process the input rule..
		# get a token, see if it fits, move on.
		buffer = ''
		appetite = True		# if hunger = 1, then, once you see one, you set to False, for ? it's ... you get the idea..

		rule = self.rules[ruleName]		# remember, .rules is a dict, and each value is a list of elements
		whatIs = self.elements[ruleName]	# now, whatIs tells you what each element of rule is - what type..
		numR = len( rule ) >> 1		# dividing by 2 gets you # of sub-rules
		
		while( appetite ) :
			depth = 0		# local depth -- as you move from left to right, you have to increment
							# so that, if you fail after finding matching tokens, you die
							# but, when you process sub-rules, you have to go back to the called depth
		
			for i in range( numR ) :
				satisfied = False
				seekToken = rule[2*i]
				count = rule[2*i + 1]	# 1 => 1; 2 => ? ; 3 => * 	-- count could be a misnomer here - it's hunger :)

				# how it works - as along as elements isn't telling you to look for a rule, you
				# take the token type (specified by the <token> ) and, if it matches then you
				# don't generate a new token tag..

				types = whatIs[i].split('||')		# from elements
				rTypes = seekToken.split('||')	# from rules
				j = 0			# this portion could be coded more elegantly for sure - more idiomatically..
				for type in types :		# that is alternatives for satisfying this token/rule
					if ( not satisfied ) :
						if( 'rule' == type ) :
							subMatch = self.analyze( rTypes[j] , count, depth>0 )	# the recursive call. severity set on the fly
							if( not ( '' == subMatch ) ):
								satisfied = True
								buffer = buffer + subMatch
								if( not re.match( '_' , rTypes[j] ) ) :
									buffer = '<' + rTypes[j] + ">\n" + buffer + '</' + rTypes[j] + ">\n"
						else : 	# not a rule, so match immediately.. good news is that hunger only applies to rules :)
							if ( self.hasMoreTokens() ) :
								if ( self.tokenName == type and re.match( rTypes[j] , self.token ) ) :
									satisfied = True
									buffer = buffer + self.nextline		# doesn't sound pretty, but..
					j = j + 1

	# example of back-tracking - varDec* - you see one variable declaration, but you're hungry for more
	# so you read a token, looking for "var", but you get "int" so you have to abort now without failing..
	# and you have to use this "int" that you just read in.. so..
					
				if ( not satisfied ) :
					if ( severe ) :
						print( "Failed when seeking match for : " + ruleName + " getting\n" + self.nextline )
						break
				
				depth = depth + 1
				
			
		return buffer
			# in the case of 2 or 3, you only add whatIs if you actually find the patterns..
		
		

		
	def hasMoreTokens( self ):
	# new twist in the tale - if you have a token waiting to be processed, because of
	# back-tracking, then you don't want to read from file..
		if( not '' == self.tokenStack ) :
			token = self.tokenStack
			self.tokenStack = ''
			return True		 # if tokenStack not empty , say True and empty it - token and tokenName would already be valid
							# spaghetti code unfortunately.. :(
		else :
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

source = sys.argv[1]		# not wasting time with prettiness here.. :)
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


		






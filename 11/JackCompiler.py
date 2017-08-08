# refer older versions for older comments 

# use cat file.xml | perl -p -e 's/\r\n/\n/g;' >> dest.xml ... to get rid of the DOS/UNIX issues

# a good idea to read comments in the SyntaxAnalyzer (project 10) first if looking at this file for the first time

# Shimon suggested having a Tokenizer here. why? That can be a separate module that generates tokens from
# raw jack code. In the SyntaxAnalyzer we said what we saw. Here, we have to do something when we see
# something - with variables, we update the symbol table ( so that's significant new functionality)

# the way it's done is to add a third dict (to rules and elements) in encode_lingo that says what
# action needs to be taken when a particular construct is encountered - for example, seeing a variable
# results in a new entry in the symbol table

# we're always processing only one class (file) at a time - for each, we create a new Analyzer and SymbolTable
# and codeWriter object

# compared to SyntaxAnalyzer, this one has a lot more comments in the encode_lingo section - essentially capturing
# the lessons from the book/video

# what's different - the SyntaxAnalyzer can just use rules and elements to infer structure from a token stream
# over here, we have an additional intelligence in the toDo dict, that tells the analyze routine what to do with
# the buffer it gets back from a slave call (recursive call to analyze). Also, buffer is no longer a string but
# a list. So, for example, consider _unOpTerm, it uses calls to convert "-xCoord" to neg and varPut xCoord but
# in postfix order.. It knows to do this because the self.toDo['_unOpTerm'] contains 
# [1, 'symbolSub', 0 , 'arithLogGen' ]
# the numbers tell the analyze routine in what order to dump the buffer contents 
# the strings tell analyze what functions to call.. (exec is what will be used eventually..)

# succinctly, terminal rules generate VM code and non-terminal rules re-arrange VM code (and add code if necessary)

import sys
import re
import pdb	# to be able to use the debugger
import textwrap
import os 	# to check if a directory has been provided
from subprocess import call # to be able to get files using *.xml

class Analyzer():

	# the only motivation for this is to be able to fold and manage the code easily :)

	def encode_lingo( self) :
		self.rules = {}		# tells you what to look for  --- not the token type, but the token itself (which could be some big thing.. like a subr)
		self.elements = {}	# tells you what tag you're going to write to the output..  -- what kind of thing satisfies each element of 'rules'
		self.toDo = {}
		# note : 1 => 1, 2 => 0 or 1 (?) , 3 => 0 or more (*)
		self.rules['class'] = ['class' , 1, '.*' , 1, '{' , 1 ,  'classVarDec' , 3, 'subroutineDec' , 3 , '}' , 1 ]
		self.elements['class'] = ['keyword', 'identifier' , 'symbol', 'rule' , 'rule' , 'symbol' ]
		self.rules['classVarDec'] = ['static|field' , 1 , '_type' , 1 , '.*' , 1 , '_addlVarDec', 3  , ';' , 1 ]	# note that static/field are "kind"
		self.elements['classVarDec'] = ['keyword' , 'rule' , 'identifier' , 'rule', 'symbol']
	# create a new entry in symbol table
		self.rules['_addlVarDec'] = [',' , 1, '.*', 1 ]		# _name implies this rule will not generate a token
		self.elements['_addlVarDec'] = ['symbol', 'identifier']
		self.rules['_type'] = ['int|char|boolean||.*' , 1]
		self.elements['_type'] = ['keyword||identifier']
		self.rules['subroutineDec'] = ['constructor|function|method' , 1 , 'void||_type' , 1 , '.*' , 1 , '\(', 1, 'parameterList' , 1 , '\)' , 1, 'subroutineBody' , 1]
		self.elements['subroutineDec'] = ['keyword' , 'keyword||rule' , 'identifier' , 'symbol' , 'rule', 'symbol', 'rule' ]
		# what this means is that you first look for keyword : void - if you see void, then your put down <keyword> void </keyword> else
		# you look at type - which is again looking for keyword : int|char|boolean .... you get the idea..
		# in the case of a void, you have to return 0... that's the VM mapping..
		
		self.rules['parameterList'] = [ '_params' , 2 ]
		self.elements['parameterList'] = ['rule']
		self.rules['_params'] = [ '_param' , 1 , '_addlParam' , 3 ]
		self.elements['_params'] = ['rule' , 'rule' ]
		self.rules['_param'] = ['_type' , 1, '.*' , 1 ]
		self.elements['_param'] = ['rule', 'identifier']
		self.rules['_addlParam' ] = [ ',' , 1 , '_type' , 1 , '.*' , 1]
		self.elements['_addlParam' ] = [ 'symbol' , 'rule', 'identifier' ]
		self.rules['subroutineBody'] = ['{' , 1 , 'varDec' , 3 , 'statements' , 1 , '}' , 1 ]
		self.elements['subroutineBody'] = ['symbol' , 'rule', 'rule', 'symbol' ]
		self.rules['varDec'] = ['var' , 1, '_type' , 1, '.*' , 1 , '_addlVarDec' , 3 , ';' , 1 ]
		self.elements['varDec'] = ['keyword' , 'rule' , 'identifier' , 'rule' , 'symbol' ]
		self.rules['statements'] = ['_statement' , 3 ]	# this was a curve ball - didn't realize they don't want <statement> ha!
		self.elements['statements'] = ['rule']
		self.rules['_statement'] = ['letStatement||ifStatement||whileStatement||doStatement||returnStatement', 1]
		self.elements['_statement'] = ['rule||rule||rule||rule||rule']
		self.rules['letStatement'] = ['let' , 1 , '.*' , 1 , '_index' , 2 , '=' , 1 , 'expression' , 1 , ';' , 1 ]
		self.elements['letStatement'] = ['keyword' , 'identifier', 'rule' , 'symbol' , 'rule', 'symbol' ]
		self.rules['_index'] = ['\[' , 1 , 'expression' , 1 , '\]' , 1 ]
		self.elements['_index'] = [ 'symbol' , 'rule' , 'symbol' ]
		self.rules['ifStatement'] = ['if' , 1 , '\(' , 1 , 'expression' , 1 , '\)' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 , '_elseBlock' , 2 ]
		self.elements['ifStatement'] = ['keyword' , 'symbol', 'rule', 'symbol', 'symbol', 'rule' , 'symbol' , 'rule' ]
		self.rules['_elseBlock' ] = ['else' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 ]
		self.elements['_elseBlock' ] = [ 'keyword', 'symbol', 'rule' , 'symbol' ]
		self.rules['whileStatement'] = ['while', 1 , '\(' , 1, 'expression' , 1 , '\)' , 1 , '{' , 1 , 'statements' , 1 , '}' , 1 ]
		self.elements['whileStatement'] = ['keyword' , 'symbol' , 'rule', 'symbol' , 'symbol' , 'rule' , 'symbol' ]
		self.rules['doStatement'] = ['do' , 1 , '_subroutineCall' , 1 , ';' , 1 ]
		self.elements['doStatement'] = ['keyword' , 'rule' , 'symbol' ]
		self.rules['returnStatement'] = ['return' , 1 , 'expression' , 2 , ';' , 1 ]
		self.elements['returnStatement'] = ['keyword' , 'rule' , 'symbol' ]
		self.rules['expression'] = ['term' , 1 , '_subExp' , 3 ]
		self.elements['expression'] = ['rule' , 'rule' ]
		# expression doesn't need to do anything smart - just dump VM commands from term and _subExp
		self.toDo['expression'] = [0, 'dump', 1 , 'dump' ]
		
		self.rules['_subExp'] = ['[+\-*/|=]|&lt;|&gt;|&amp;' , 1 , 'term' , 1 ]	# intended for us in a regex search -- 
		self.elements['_subExp'] = ['symbol' , 'rule']	# special case - CSV - the rule-entry - in this case op will go out as <op> CSV-item </op>
		self.toDo['_subExp'] = [1, 'vmgen.writeArithmetic(', 0 , 'n/a']
		
		self.rules['term'] = ['_subroutineCall||_arrayElem||integerConstant||stringConstant||_keywordConstant||_varName||_paranthExp||_unOpTerm' , 1]
		self.elements['term'] = ['rule||rule||rule||rule||rule||rule||rule']	
		self.rules['integerConstant'] = ['.*' , 1]
		self.elements['integerConstant'] = ['integerConstant']
		self.toDo['integerConstant'] = [ 0 , "vmgen.writePush( 'constant ' , " ]
		
		self.rules['stringConstant'] = ['.*', 1]
		self.elements['stringConstant'] = ['stringConstant']
		self.toDo['stringConstant'] = [ 0 , '' ]
		
		self.rules['_arrayElem'] = ['.*' , 1 , '\[' , 1 , 'expression' , 1 , '\]' , 1 ]
		self.elements['_arrayElem'] = ['identifier' , 'symbol', 'rule' , 'symbol' ]
		self.rules['_paranthExp'] = ['\(' , 1 , 'expression' , 1, '\)' , 1]
		self.elements['_paranthExp'] = ['symbol' , 'rule' , 'symbol' ]
		self.toDo['_paranthExp'] = [ 1 , 'n/a' , 0 , 'dump' , 2, 'n/a' ]
		
		self.rules['_unOpTerm' ] = ['[-~]' , 1 , 'term' , 1 ]
		self.elements['_unOpTerm' ] = ['symbol', 'rule']	# this is another special case - a CSV -- you put the rule-entry - in this case, <unaryOp>
		self.toDo['_unOpTerm'] = [ 1 , 'vmgen.arithLogGen(' , 0 , 'symTab.symbolSub(' ]
		
		self.rules['_subroutineCall' ] = [ '.*' , 1 , '_cmCallMarker' , 2 , '\(' , 1, 'expressionList' , 1 , '\)' , 1 ]
		self.elements['_subroutineCall' ] = [ 'identifier' , 'rule' , 'symbol' , 'rule' , 'symbol' ]
		self.rules['_cmCallMarker'] = ['\.' , 1, '.*' , 1]
		self.elements['_cmCallMarker'] = [ 'symbol' , 'identifier' ]
		self.rules['expressionList' ] = [ '_expressions' , 2 ] 
		self.elements['expressionList'] = [ 'rule']
		self.rules['_expressions'] = [ 'expression' , 1 , '_addlExpr' , 3 ]
		self.elements['_expressions'] = ['rule' , 'rule']
		self.rules['_addlExpr'] = [',' , 1 , 'expression' , 1 ]
		self.elements['_addlExpr'] = ['symbol' , 'rule']
		self.rules['_keywordConstant' ] = ['true|false|null|this', 1]
		self.elements['_keywordConstant'] = ['keyword']
		self.rules['_varName'] = ['.*', 1]
		self.elements['_varName'] = ['identifier']
		# op and unaryOp were also curve balls - be clear - say that those will not generate tokens!!

	def __init__( self, filename ):
		self.instream = open( filename, "r")	# be nice to do some exception handling :)
		target = re.sub( "Tokens\.xml" , "Analyzed.xml" , filename )
		vmtgt = re.sub( "Tokens\.xml" , ".vm" , filename )
		self.outstream = open( target, "w" )
		self.vmstream = open( vmtgt, "w" )
		self.nextline = ''
		self.tokenStack = []		# this enables backtracking - you have a token you read, now you have to 
									# stop processing this rule and process another one - so you have to
									# reuse the existing token
		self.lineN = 1
		self.encode_lingo()
		self.vmgen = VMWriter()
		self.symTab = SymbolTable()

	def Write( self, buffer ) :		# buffer could be very big - so might need a better way to deal with this
		self.outstream.write( buffer )
		self.outstream.close()

	def WriteVM( self, bufVM ) :		# buffer could be very big - so might need a better way to deal with this
		self.vmstream.write( bufVM )
		self.vmstream.close()
		
	# big change here is that VM command list (of strings) and the token buffer are returned..
	# this is the main operator that uses other methods - maybe an OO noob style deprecated, but..	
	# elements[xyz][] -- if you see 'rule', that results in another call to analyze()
	#					-- if you see || then you split on || and process the resulting list in OR fashion - first one that hits terminates
	# also, hunger can only get elevated when traversing a rule laterally -- going by LL1..
	def analyze( self, ruleName, hunger ) :		# hunger is the same as 1,2,3 for 1, ?, *
		# returns a buffer containing tokens satisfying rule, or ''. If return is '', then 
		# decide if input is bad based on hunger and depth
		# pdb.set_trace()
		# will call itself recursively when it uses self.rules[] to process the input rule..
		# get a token, see if it fits, move on.
		buffer = ''		# this one stays as it is to support back-tracking
		VMbuf = []
		final = ''	# more spaghettiness..
		VMfinal = ''
		sought = ''
		appetite = True		# if hunger = 1, then, once you see one, you set to False, for ? it's ... you get the idea..

		rule = self.rules[ruleName]		# remember, .rules is a dict, and each value is a list of elements
		whatIs = self.elements[ruleName]	# now, whatIs tells you what each element of rule is - what token, or what (other) rule to look for
		numR = len( rule ) >> 1		# dividing by 2 gets you # of sub-rules
		howMany = 0;
		hits = [False] * numR
		capture = ''	# intended for use by exec

		while( appetite ) :
			VMbuf = [''] * numR
			depth = 0		# local depth -- as you move from left to right, you have to increment
							# so that, if you fail after finding matching tokens, you die
							# but, when you process sub-rules, you have to go back to the called depth
		
			for i in range( numR ) :
				satisfied = False
				seekToken = rule[2*i]
				need = rule[2*i + 1]	# 1 => 1; 2 => ? ; 3 => * 	# note that the higher need is, the fewer you actually need to match

				# how it works - as along as elements isn't telling you to look for a rule, you
				# take the token type (specified by the <token> ) and, if it matches then you
				# don't generate a new token tag.. (that is, you dump out what you read..)

				types = whatIs[i].split('||')		# from elements

				rTypes = seekToken.split('||')	# from rules
				j = 0			# this portion could be coded more elegantly for sure - more idiomatically..
				for type in types :		# that is alternatives for satisfying this token/rule
					if ( not satisfied ) :
						# pdb.set_trace()
						if( 'rule' == type ) :
							[subMatch, result, subVM ] = self.analyze( rTypes[j] , need )	# the recursive call. severity set on the fly
							if( (not ( '' == subMatch ) ) and (not re.search('fail' , subMatch ) ) ) :
								satisfied = True
								buffer = buffer + subMatch
								if( ruleName in self.toDo ) : 
									VMbuf[ self.toDo[ ruleName ][ 2*i ] ] = subVM
								else :
									VMbuf[ i ] = subVM
								hits[ i ] = True
							if( '' == subMatch and 1 < need ) :
								satisfied = True	# question : do we ever have xyz||rule with ?/*?
							if( result ) :
								satisfied = True	# rookie code, but..
						else : 	# not a rule, so match immediately.. good news is that hunger only applies to rules :)
							if ( self.hasMoreTokens() ) :
								sought = rTypes[j]
								if ( self.tokenName == type and re.match( rTypes[j] , self.token ) ) :
									satisfied = True
									hits[ i ] = True
									buffer = buffer + self.nextline		# doesn't sound pretty, but..
									if( ruleName in self.toDo ) : 
										if( not 'n/a' == self.toDo[ ruleName][2*i + 1] ) :
											# pdb.set_trace()
											# cmd = 'capture = self.' + self.toDo[ ruleName ][2*i + 1] + " '" + self.token + "' )"
											exec( 'capture = self.' + self.toDo[ ruleName ][2*i + 1] + " '" + self.token + "' )"  )
											VMbuf[ self.toDo[ ruleName ][ 2*i ] ] = capture # the order is also right 
																							# onus is now on encode_lingo

								else :		# went weeks without this :)
									self.tokenStack = [self.nextline] + self.tokenStack
					j = j + 1
				# for type in types

				if( not satisfied ) :
					if ( depth > 1 ) :
						print( "Bad end to long token chain .." + ruleName + " : " + buffer )
						sys.exit()
					if( not '' == buffer ) :
						self.tokenStack = buffer.rstrip("\n").rstrip("\r").split( r"\r?\n")
						tokenStack = []
						for token in self.tokenStack :
							tokenStack = tokenStack + [token + "\n"]
						self.tokenStack = tokenStack
						self.tokenStack = self.tokenStack + [self.nextline]

	# example of back-tracking - varDec* - you see one variable declaration, but you're hungry for more
	# so you read a token, looking for "var", but you get "int" so you have to abort now without failing..
	# and you have to use this "int" that you just read in.. so..
					
#				pdb.set_trace()
				if ( not satisfied ) :
					if ( 1==hunger ) :
						return ['fail : ' + ruleName, False, VMfinal ]
					else :
						return [final, not( '' == final), VMfinal ]
				
				if ( 1 == need ) :
					depth = depth + 1	# only keep track of mandatory items... :) 5/24 -- late in the game realization :)
				
			# for i in range( numR )

			if( satisfied  ) :	# check for '' if you don't want tags for empty stuff..
				howMany = howMany + 1
				if( 3 > hunger ) :		# meaning hunger is 1 or 2, so you are done looking..
					appetite = False
				if( not re.match( '_' , ruleName ) ) :
					buffer = '<' + ruleName + ">\n" + re.sub(r"^(.)" , r"  \1", buffer , flags=re.MULTILINE) + '</' + ruleName + ">\n"	
				final = final + buffer
				buffer = ''
				VMfinal = VMfinal +  "\n".join( VMbuf )
			else :
				return [final, satisfied, VMfinal ]		# lame spaghetti code, but just get it working for now..

#		pdb.set_trace()
		return [final, satisfied, VMfinal ]		# takes care of the "satisfied" case - where you'll observe you 
												# can't have a return statement because of the hunger = 3 case..
			# in the case of 2 or 3, you only add whatIs if you actually find the patterns..
		
		
	def hasMoreTokens( self ):
	# new twist in the tale - if you have a token waiting to be processed, because of
	# back-tracking, then you don't want to read from file..
		if( len( self.tokenStack ) ) :
			self.nextline = self.tokenStack[0]
			match = re.match( "^\s*<(\S+)>\s*(\S+)" , self.nextline )
			if( match ) :
				self.tokenName = match.group(1)
				self.token = match.group(2)
			self.tokenStack = self.tokenStack[1:]
			return True		 # if tokenStack not empty , say True and empty it - token and tokenName would already be valid
							# spaghetti code unfortunately.. :(
		else :
			self.nextline = self.instream.readline();
			# print( self.nextline )
			# print( '_____________________________====================================')
			self.lineN = self.lineN + 1
			if not self.nextline:
				return False
			else:
				if( re.match( '<\/?tokens>' , self.nextline ) ) :
					self.nextline = self.instream.readline()
				match = re.match( "^\s*<(\S+)>\s*(\S+)" , self.nextline )
				if( match ) :
					self.tokenName = match.group(1)
					self.token = match.group(2)
				else :
					return False
				return True
			
			

class SymbolTable :
	# maintain 2 dicts - one for the fields and one for the sub vars - locals and arguments
	# essentially, the symbol table is a scratchpad that assists you in code-generation..

	def __init__( self ) :
		self.c_table = {}
		self.c_index = 0
	
	
	def startSubroutine() :	# this guy just clears the sub symbol table
		self.s_table = {}
		self.s_index = 0
	
	def Define( name, type, kind ) :	# string, string, STATIC, FIELD, ARG or VAR -- creates a new entry in the table 
										# static and field are class scope, arg and var are sub scope
		if( kind in ['STATIc', 'FIELD'] ) :
			self.c_table[ name ] = [ self.c_index, type, kind ]
			self.c_index += 1
		else :
			self.s_table[ name ] = [ self.s_index, type, kind ]
			self.s_index += 1
	
	def varCount( kind ) :		# return int and takes STATIC, FIELD, ARG or VAR
								# "how many of this kind are already defined in current scope?"
		if( kind in ['STATIC', 'FIELD'] ) :
			return sum( var[ 2 ] == kind for var in c_table )
		else :
			return sum( var[ 2 ] == kind for var in s_table )
								
	def kindOf( name ) :		# returns STATIC, FIELD.. of the given identifier by referencing the dicts
		if( self.s_table[ name ] ) :
			return self.s_table[ name ][ 2 ]
		elif( self.c_table[ name ] ) :
			return self.c_table[ name ][ 2 ]
		else :
			return 'NONE'
			
	def typeOf( name ) :
		if( self.s_table[ name ] ) :
			return self.s_table[ name ][ 1 ]
		elif( self.c_table[ name ] ) :
			return self.c_table[ name ][ 1 ]
		else :
			return 'NONE'
	
	def indexOf( name ) :
		if( self.s_table[ name ] ) :
			return self.s_table[ name ][ 0 ]
		elif( self.c_table[ name ] ) :
			return self.c_table[ name ][ 0 ]
		else :
			return -1
			
	def symbolSub( name ) :
		return 'dummy for now'

			
class VMWriter :
# with the scheme I've chosen for analysis, having an object here makes no sense - so, in our case, it's just a library of functions
# that the Analyzer can use to generate VM code

	def __init__( self ) :
		return None
		
	def writePush( self, segment, index ) :	# CONST, ARG, LOCAL, STATIC, THIS, THAT, POINTER, TEMP and integer for index
		return 'push ' + segment + str( index ) + "\n" 
		
	def writePop( self, segment, index ) :
		return 'pop ' + segment + str( index )  + "\n" 
	
	def writeArithmetic( self, cmd ) :
		VMcmd = cmd
		if( '+' == cmd ) :
			VMcmd = 'add'
		elif( '-' == cmd ) :
			VMcmd = 'sub'
		elif( '/' == cmd ) :
			VMcmd = 'call Math.divide 2'
		elif( '*' == cmd ) :
			VMcmd = 'call Math.multiply 2'
		elif( '=' == cmd ) :
			VMcmd = 'eq'
		elif( '&lt;' == cmd ) :
			VMcmd = 'lt'
		elif( '&gt;' == cmd ) :
			VMcmd = 'gt'
		elif( '&amp;' == cmd ) :
			VMcmd = 'and'

		return VMcmd  + "\n" 

	def writeUnary( self, cmd ) :
		VMcmd = cmd
		if( '-' == cmd ) :
			VMcmd = 'neg'
		elif( '~' == cmd ) :
			VMcmd = 'not'
		return VMcmd  + "\n" 
		
	def writeLabel( label ) :
		return 'label ' + label + "\n" 
	
	def writeGoto( label ) :
		return 'goto ' + label + "\n" 
		
	def writeIf( label ) :
		return 'if-goto ' + label + "\n" 
		
	def writeCall( name, nArgs ) :
		return 'call ' + name + ' ' + str( nArgs ) + "\n" 
	
	def writeFunction( name, nLocals ) :
		return 'function ' + name + ' ' + str( nLocals ) + "\n" 
	
	def writeReturn( ) :
		return "return\n" 
		

			
# Main program :

# if a directory "Adder" is input containing .jack files, then the output is Adder/File1.xml - for each..

# if no files in the specified source, then die..

source = sys.argv[1]		# not wasting time with prettiness here.. :)
# pdb.set_trace()	

state = 'START';
buffer = '';

if os.path.isdir( source ) :
	# start off writing to source/fileAnalyzed.xml by processing every .jack file you encounter
	filelist = os.popen( "ls " + source + "/*.jack").read().split()
	if len( filelist ) < 1 :
		print( "Please check if the directory has .jack files in it (Eg. SquareTokens.jack" )
else :
	if re.search( r".jack" , source ) :
		filelist = [source]
	else :
		print( "Only operates on .jack files" )
		sys.exit()

pdb.set_trace()
		
for file in filelist :
	call( ["python",  "Tokenizer.py" , file] )
	# system call for generating nameTokens.xml from the name.jack
	xml = re.sub( "\.jack" , "Tokens.xml" , file )
	j_analyzer = Analyzer( xml )	# this does an init and also open the target for writing..
	[buf, state, VMcmds] = j_analyzer.analyze('class' , 1 )
	j_analyzer.Write( buf )
	j_analyzer.WriteVM( re.sub( r"\n+" , r"\n", VMcmds , flags=re.MULTILINE)  )


		






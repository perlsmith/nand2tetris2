# refer older versions for older comments 

# use cat file.xml | perl -p -e 's/\r\n/\n/g;' >> dest.xml ... to get rid of the DOS/UNIX issues

# note, this impl assumes constructor return type is right and that the constructor returns "this". It only adds a return 0
# for the case of void. http://www.shimonschocken.com/nand2tetris/lectures/PDF/lecture%2009%20high%20level%20language.pdf (slide 14)

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
	# toDo contains command - it could probably just be a list, but is a dict for now
	# the number is (when positive) the position of the final return array that the result of the exce goes in..
	# when negative, it's a command code : -2 means just execute literally. -1 means substitute % with self.token. 
	# spaghetti coded implementation because orthogonality is very poor - this section needs to know about code in the analyze section..
	# -3 is only applicable for the case of the sought token being a non-terminal rule..

	def encode_lingo( self) :
		self.rules = {}		# tells you what to look for  --- not the token type, but the token itself (which could be some big thing.. like a subr)
		self.elements = {}	# tells you what tag you're going to write to the output..  -- what kind of thing satisfies each element of 'rules'
		self.toDo = {}		# tells you what to do when processing each rule -- key tells you in what 
		# note : 1 => 1, 2 => 0 or 1 (?) , 3 => 0 or more (*)
		self.rules['class'] = ['class' , 1, '.*' , 1, '{' , 1 ,  'classVarDec' , 3, 'subroutineDec' , 3 , '}' , 1 ]
		self.elements['class'] = ['keyword', 'identifier' , 'symbol', 'rule' , 'rule' , 'symbol' ]
			# Nothing to be done here, because the constructor for the Analyzer already initializes the symbol Table
		
		self.rules['classVarDec'] = ['static|field' , 1 , '_type' , 1 , '.*' , 1 , '_addlVarDec', 3  , ';' , 1 ]	# note that static/field are "kind"
		self.elements['classVarDec'] = ['keyword' , 'rule' , 'identifier' , 'rule', 'symbol']
	# create a new entry in symbol table
		# here, you also need feed-forward communication (ain't this the definition of spaghetti code?)
		# because, classVarDec knows type, but _addlVarDec does not.. -- this necessitates a self.currentType that _addlVarDec can use.. what a shame:) but Elon Musk would like it..
		# So, here, _type needs to set currentType and the classVarDec only needs to upate the symbol Table with the identifier
		self.toDo['classVarDec'] = [ -1 , "self.currentKind = '%'" , 0 , 'n/a' , 0 , "self.symTab.Define(  self.currentType, self.currentKind, '%')" , 0 , 'n/a', 0, 'n/a']
		# again - sad to have to use this - when analyze sees a '-1', it'll just excecute, rather than executing and capturing :(  spaghetti code :(
	
		self.rules['_addlVarDec'] = [',' , 1, '.*', 1 ]		# _name implies this rule will not generate a token
		self.elements['_addlVarDec'] = ['symbol', 'identifier']
		self.toDo['_addlVarDec'] = [0, 'n/a' , -1 , "self.symTab.Define( self.currentType, self.currentKind, '%')"]	# very similar to what classVarDec does - this one depends on that to set kind, type
		
		self.rules['_type'] = ['int|char|boolean||.*' , 1]
		self.elements['_type'] = ['keyword||identifier']
		self.toDo['_type'] = [ -1 , "self.currentType = '%'"]
		
		self.rules['subroutineDec'] = ['constructor|function|method' , 1 , 'void||_type' , 1 , '.*' , 1 , '\(', 1, 'parameterList' , 1 , '\)' , 1, 'subroutineBody' , 1]
		self.elements['subroutineDec'] = ['keyword' , 'keyword||rule' , 'identifier' , 'symbol' , 'rule', 'symbol', 'rule' ]
		self.toDo['subroutineDec'] = [ -1 , "self.currentFnKind = '%'" , -1 , "self.currentFnType = '%'\nself.symTab.startSubroutine()" , 
										-1, "self.currentName = '%'",  -2 , "self.currentKind = 'argument'",  0 , 'n/a' ,
										-2 , "self.currentKind = 'local'\nself.symTab.Define( self.currentFnType, self.currentFnKind, 'function.' + self.currentName)" , 0 , 'n/a' ]
		# what this means is that you first look for keyword : void - if you see void, then your put down <keyword> void </keyword> else
		# you look at type - which is again looking for keyword : int|char|boolean .... you get the idea..
		# in the case of a void, you have to return 0... that's the VM mapping..
		# although Shimon failed to mention it, we'll update the symbol table with functions as well - until we figure out a way
		# that the implementation doesn't need it... You see here that the subroutine declaration header generates no VM code - this is because we don't know the
		# nLocals :( ... so that's why we're feeding forward the currentName to the subroutineBody in spaghetti style
		# very, very spaghetti :(
		# see kind (constructor, etc..) : set currentFnKind
		# see return type : set currentType       AND   also initialize the subroutine symbol table
		# see name : set currentName ( so that a downstream piece of code has this ready..
		# see (  : get ready to process arg list by setting currentKind to argument
		# see ) : set currentKind to 'local' AND  enter this function name into the symbol function table - so that the subroutineBody guy can insert a return if needed..
		
		self.rules['parameterList'] = [ '_params' , 2 ]
		self.elements['parameterList'] = ['rule']
		# does parameterList need to generate VM code or update the symbol table? Yes - coz the function needs to access these.. 
		
		self.rules['_params'] = [ '_param' , 1 , '_addlParam' , 3 ]
		self.elements['_params'] = ['rule' , 'rule' ]
		self.rules['_param'] = ['_type' , 1, '.*' , 1 ]
		self.elements['_param'] = ['rule', 'identifier']
		self.toDo['_param'] = [ -1 , "self.currentType = '%'" , -1 , "self.symTab.Define( self.currentType, self.currentKind, '%')" ]
		
		self.rules['_addlParam' ] = [ ',' , 1 , '_type' , 1 , '.*' , 1]
		self.elements['_addlParam' ] = [ 'symbol' , 'rule', 'identifier' ]
		self.toDo['_addlParam'] = [ 0, 'n/a', -1 , "self.currentType = '%'" , -1 , "self.symTab.Define( self.currentType, self.currentKind, '%')" ]
		
		
		self.rules['subroutineBody'] = ['{' , 1 , 'varDec' , 3 , 'statements' , 1 , '}' , 1 ]
		self.elements['subroutineBody'] = ['symbol' , 'rule', 'rule', 'symbol' ]
		self.toDo['subroutineBody'] = [ -2 , 'self.nLocals = 0' , -3, "self.vmgen.construct( self.currentFnKind, self.currentName, self.nLocals)", 
										0, 'n/a' , 1, "self.vmgen.writeReturn( self.currentFnType, True )" ]
		# here, when varDec is done, it returns numMatch - which you should now use to enter "function currentName nLocals" correctly..
		# pending - use the final } to put out a return 0 in the case of a void or a constructor (where you have to return this -- if you ask me, the syntax should require it)
		
		self.rules['varDec'] = ['var' , 1, '_type' , 1, '.*' , 1 , '_addlVarDec' , 3 , ';' , 1 ]
		self.elements['varDec'] = ['keyword' , 'rule' , 'identifier' , 'rule' , 'symbol' ]
		self.toDo['varDec'] = [ -2, "self.nLocals = self.nLocals + 1",  -1 , "self.currentType = '%'", 
									0 ,	"self.symTab.Define(  self.currentType, self.currentKind, '%' )", -3 , "self.nLocals = self.nLocals + numMatch", 0, 'n/a']


		self.rules['statements'] = ['_statement' , 3 ]	# this was a curve ball - didn't realize they don't want <statement> ha!
		self.elements['statements'] = ['rule']
		self.rules['_statement'] = ['letStatement||ifStatement||whileStatement||doStatement||returnStatement', 1]
		self.elements['_statement'] = ['rule||rule||rule||rule||rule']
		self.rules['letStatement'] = ['let' , 1 , '.*' , 1 , '_index' , 2 , '=' , 1 , 'expression' , 1 , ';' , 1 ]
		self.elements['letStatement'] = ['keyword' , 'identifier', 'rule' , 'symbol' , 'rule', 'symbol' ]
		self.toDo['letStatement'] = [0, 'n/a' , -1, "self.currentName = '%'\n" ,
										-1, "self.a_index=subVM", 1, "self.vmgen.writeLHS( self.symTab.seg_ind( self.currentName), self.a_index )", 0, 'dump', 0, 'n/a'  ]
		# this stuff is magic - if the name has a . in it, then you use the this pointer to access the field..
		# on the LHS, you need to pop - in postfix sense - that is, you first build up the expression given by the RHS using a series
		# of push commands, and function calls, and then you pop into the segment/index specified by the LHS
		### for the moment, ignoring array elements..     #### will eventually need a standalone function to make this magic work..		
		
		
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
		self.toDo['returnStatement'] = [ 0, 'n/a', -3 , "subVM = self.vmgen.writeReturn( subVM, False )", 0, 'n/a']
		
		self.rules['expression'] = ['term' , 1 , '_subExp' , 3 ]
		self.elements['expression'] = ['rule' , 'rule' ]
		# expression doesn't need to do anything smart - just dump VM commands from term and _subExp
		self.toDo['expression'] = [0, 'dump', 1 , 'dump' ]
		
		self.rules['_subExp'] = ['[+\-*/|=]|&lt;|&gt;|&amp;' , 1 , 'term' , 1 ]	# intended for us in a regex search -- 
		self.elements['_subExp'] = ['symbol' , 'rule']	# special case - CSV - the rule-entry - in this case op will go out as <op> CSV-item </op>
		self.toDo['_subExp'] = [1, "self.vmgen.writeArithmetic( '%' )", 0 , 'n/a']
		
		self.rules['term'] = ['_subroutineCall||_arrayElem||integerConstant||stringConstant||_keywordConstant||_varName||_paranthExp||_unOpTerm' , 1]
		self.elements['term'] = ['rule||rule||rule||rule||rule||rule||rule']	
		self.rules['integerConstant'] = ['.*' , 1]
		self.elements['integerConstant'] = ['integerConstant']
		self.toDo['integerConstant'] = [ 0 , "self.vmgen.writePush( 'constant ' , '%' )" ]
		
		self.rules['stringConstant'] = ['.*', 1]
		self.elements['stringConstant'] = ['stringConstant']
		self.toDo['stringConstant'] = [ 0 , "self.vmgen.createString( '%' )" ]		# here, you have to construct the string with a series of calls to String.appendChar - start with String.new first :)
		
		self.rules['_arrayElem'] = ['.*' , 1 , '\[' , 1 , 'expression' , 1 , '\]' , 1 ]
		self.elements['_arrayElem'] = ['identifier' , 'symbol', 'rule' , 'symbol' ]
		self.toDo['_arrayElem'] = [0, "self.vmgen.writePushPop( 'push' , self.symTab.seg_ind('%') )", 0, 'n/a', 
								-3, "subVM + self.vmgen.writeArrayElem( False )" , 0, 'n/a']
		
		self.rules['_paranthExp'] = ['\(' , 1 , 'expression' , 1, '\)' , 1]
		self.elements['_paranthExp'] = ['symbol' , 'rule' , 'symbol' ]
		self.toDo['_paranthExp'] = [ 1 , 'n/a' , 0 , 'dump' , 2, 'n/a' ]
		
		self.rules['_unOpTerm' ] = ['[-~]' , 1 , 'term' , 1 ]
		self.elements['_unOpTerm' ] = ['symbol', 'rule']	# this is another special case - a CSV -- you put the rule-entry - in this case, <unaryOp>
		self.toDo['_unOpTerm'] = [ 1 , "self.vmgen.arithLogGen('%')" , 0 , "self.vmgen.writePushPop( 'push', self.symTab.seg_ind('%') )" ]
		
		self.rules['_subroutineCall' ] = [ '.*' , 1 , '_cmCallMarker' , 2 , '\(' , 1, 'expressionList' , 1 , '\)' , 1 ]
		self.elements['_subroutineCall' ] = [ 'identifier' , 'rule' , 'symbol' , 'rule' , 'symbol' ]
		# here's where you have to pull the rabbit out of the hat -- for a constructor, you don't care. But, for a function, if return type is void,
		# then you have to insert a return 0.. (push constant 0, return )
		# if it's a method, then you have to first of all add 1 to the nArgs and set ARG #0 to the address of the object (this)
		# and then you have to also check for void and insert return 0 if necessary. 
		
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
		self.toDo['_keywordConstant'] = [ 0, "self.vmgen.writeConst('%')" ]
		
		self.rules['_varName'] = ['.*', 1]
		self.elements['_varName'] = ['identifier']
		self.toDo['_varName'] = [ 0, "self.vmgen.writePushPop( 'push' , self.symTab.seg_ind('%') )"]
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
		self.currentKind = ''
		self.currentFnKind = ''		# all helpers for the spaghetti code - the problem is that function definition contains the variable declarations - which also need kind :( (local)
		self.currentType = ''
		self.currentName = ''
		self.a_index = ''

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
		# print ruleName + ' ' + str(hunger) + "\n"
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
		self.a_index = ''	# supporting spaghetti --> another routine buried somewhere depends on this being reset :)

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
							[subMatch, result, subVM, numMatch ] = self.analyze( rTypes[j] , need )	# the recursive call. severity set on the fly
							if( (not ( '' == subMatch ) ) and (not re.search('fail' , subMatch ) ) ) :
								satisfied = True
								buffer = buffer + subMatch
								if( ruleName in self.toDo ) : 
									if( -3 == self.toDo[ruleName][2*i] ) :
										exec( 'capture = ' + self.toDo[ ruleName ][ 2*i + 1 ] )
										VMbuf[ i ] = str(capture)
										#print( '... within  ' + ruleName + ' , ' + rTypes[j] + ' : adding ' + capture )
									elif( -1 == self.toDo[ruleName][2*i] ) :		# started with classVarDec :) -- here, no need to do a capture
										cmd = re.sub( '%' , self.token, self.toDo[ ruleName ][ 2*i + 1 ] )
										exec( cmd  )
									elif ( not 'disregard' == self.toDo[ ruleName ][ 2*i + 1 ] ) :
										VMbuf[ self.toDo[ ruleName ][ 2*i ] ] = subVM
										#print( '... within  ' + ruleName + ' , ' + rTypes[j] + ' : adding ' + subVM )
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
											if( -2 == self.toDo[ruleName][2*i] ) :		# here, not only no capture, we don't add anything to the code in the toDo item..
												exec( self.toDo[ ruleName ][ 2*i + 1 ] )
											elif( -1 == self.toDo[ruleName][2*i] ) :		# started with classVarDec :) -- here, no need to do a capture
												cmd = re.sub( '%' , self.token, self.toDo[ ruleName ][ 2*i + 1 ] )
												exec( cmd  )				# documentation failure - where do you need the execution and the assignment of token?
												# VMbuf[ self.toDo[ ruleName ][ 2*i ] ] = self.token		# this way, _type can do double duty :) sorry for spaghetti :)
											else :
												# pdb.set_trace()
												# cmd = 'capture = self.' + self.toDo[ ruleName ][2*i + 1] + " '" + self.token + "' )"
												# exec( 'capture = self.' + self.toDo[ ruleName ][2*i + 1] + " '" + self.token + "' )"  )	# so, it's whatever you got, and then here we add token
												## had to retire the above way because I couldn't handle fn1( fn2 ( self.token ) ) with that approach - easier to substitute % with.. and call
												cmd = 'capture = ' + re.sub( '%', self.token, self.toDo[ ruleName ][ 2*i + 1 ] )
												print cmd + "\n"
												exec( cmd )
												VMbuf[ self.toDo[ ruleName ][ 2*i ] ] = str(capture) # the order is also right 
																								# onus is now on encode_lingo
																								# we need this form of indexing just to get the postfix thing right..
										#print( '... within  ' + ruleName + ' , ' + rTypes[j] + ' : adding (token match) .. ' + capture )
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
						return ['fail : ' + ruleName, False, VMfinal, howMany ]
					else :
						return [final, not( '' == final), VMfinal, howMany ]
				
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
				return [final, satisfied, VMfinal, howMany ]		# lame spaghetti code, but just get it working for now..

#		pdb.set_trace()
		return [final, satisfied, VMfinal, howMany ]		# takes care of the "satisfied" case - where you'll observe you 
												# can't have a return statement because of the hunger = 3 case..
			# in the case of 2 or 3, you only add whatIs if you actually find the patterns..
		
		
	def hasMoreTokens( self ):
	# new twist in the tale - if you have a token waiting to be processed, because of
	# back-tracking, then you don't want to read from file..
		if( len( self.tokenStack ) ) :
			self.nextline = self.tokenStack[0]
			match = re.match( r"^\s*<(\S+)>\s*(\S.*?)\s*</\1" , self.nextline )
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
				match = re.match( r"^\s*<(\S+)>\s*(\S.*?)\s*</\1" , self.nextline )
				if( match ) :
					self.tokenName = match.group(1)
					self.token = match.group(2)
				else :
					return False
				return True
			
			

class SymbolTable :
	# maintain 2 dicts - one for the fields and one for the sub vars - locals and arguments
	# essentially, the symbol table is a scratchpad that assists you in code-generation..
	# if the var is not of a known type - int, char, boolean - then it's a class - and that's what happeneth to String..

	def __init__( self ) :
		self.s_table = {}	# static segment
		self.t_table = {}	# 'this' segment (field variables)
		self.t_index = 0
		self.s_index = 0
		self.f_table = {}
	
	
	def startSubroutine( self ) :	# this guy just clears the sub symbol table
		# print "Doing fn var table init\n"
		self.l_table = {}	# local segment
		self.l_index = 0
		self.a_table = {}	# argument segment
		self.a_index = 0
	
	def Define( self, type, kind, name ) :	# string, STATIC, FIELD, ARG or VAR and string -- creates a new entry in the table 
										# static and field are class scope, arg and var are sub scope; can't have arg and local vars named the same..
		if( kind == 'argument' ) :
			self.a_table[ name ] = [ self.a_index, type ]
			self.a_index += 1
		elif ( kind == 'local' ) :
			self.l_table[ name ] = [ self.l_index, type ]
			self.l_index += 1
		elif( kind == 'static' ) :
			self.s_table[ name ] = [ self.s_index, type ]
			self.s_index += 1
		elif( kind == 'field' ) :	
			self.t_table[ name ] = [ self.t_index, type ]
			self.t_index += 1
		else :
			self.f_table[ name ] = [type, kind]			# kind will be constructor|function|method and type will be return type - void or whatever
		return ''
	
	def varCount( self,  kind ) :		# return int and takes STATIC, FIELD, ARG or VAR
								# "how many of this kind are already defined in current scope?"
		if( kind in ['STATIC', 'FIELD'] ) :
			return sum( var[ 2 ] == kind for var in c_table )
		else :
			return sum( var[ 2 ] == kind for var in s_table )
								
	def kindOf( self, name ) :		# returns STATIC, FIELD.. of the given identifier by referencing the dicts
		if( self.s_table[ name ] ) :
			return self.s_table[ name ][ 2 ]
		elif( self.c_table[ name ] ) :
			return self.c_table[ name ][ 2 ]
		else :
			return 'NONE'
			
	def typeOf( self, name ) :
		if( self.s_table[ name ] ) :
			return self.s_table[ name ][ 1 ]
		elif( self.c_table[ name ] ) :
			return self.c_table[ name ][ 1 ]
		else :
			return 'NONE'
	
	def seg_ind( self, name ) :
		if( name in self.a_table ) :		# first go to argument segment -- truly even local could be first..
			return 'argument ' + str( self.a_table[ name ][ 0 ] )
		elif( name in self.l_table ) :
			return 'local ' + str( self.l_table[ name ][ 0 ] )
		elif( name in self.s_table ) :
			return 'static ' + str( self.s_table[ name ][ 0 ] )
		elif( name in self.t_table ) :
			return 'this ' + str( self.t_table[ name ][ 0 ] )
		else :			# unknown variable name
			return name + ' ' + str(-1)
			


			
class VMWriter :
# with the scheme I've chosen for analysis, having an object here makes no sense - so, in our case, it's just a library of functions
# that the Analyzer can use to generate VM code

	def __init__( self ) :
		return None
		
	def construct( self , kind, name, nLocals ) :
		VMcmd = "function " + name + ' ' + str(nLocals) + "\n"
		if 'constructor' == kind :
			VMcmd += "push constant " + str(nLocals) + "\n"
			VMcmd += "call Memory.alloc 1\n"
			VMcmd += "pop pointer 0\n" 		# sets the 'this' segment
		return VMcmd
		
	def createString( self, string ) :
		VMcmd = "push constant " + str( len( string ) ) + "\n"
		VMcmd += "call String.new 1\n"	# remember nArgs - and the fact that String is a class!
		for char in string :
			VMcmd = VMcmd + "push " + str(ord( char )) + "\n"
			VMcmd = VMcmd + "call String.appendChar 2\n"
		return VMcmd
	
	def writePush( self, segment, index ) :	# CONST, ARG, LOCAL, STATIC, THIS, THAT, POINTER, TEMP and integer for index
		return 'push ' + segment + str( index ) + "\n" 
		
	def writePop( self, segment, index ) :
		return 'pop ' + segment + str( index )  + "\n" 
		
	def writePushPop( self, cmd, seg_ind ) :
		# print str(seg_ind) + "\n"
		return cmd + ' ' + seg_ind + "\n"
	
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
	
	def writeReturn( self, what, isInlineCmd ) :
		if ( 'void' == what and isInlineCmd) :
			return  "push constant 0\nreturn\n"
		elif( not isInlineCmd ) :		# essentially supporting spaghetting code
			return what + "\nreturn\n"
		else :
			return ''
		
	def writeArrayElem( self, lhsRHZB ) :
		VMcmd = "add\n"
		VMcmd += "pop pointer 1		// setting 'that'\n"
		if lhsRHZB :
			VMcmd += "pop that 0\n"
		else :			# meaning what's in the mem gets used, not updated..
			VMcmd += "push that 0\n"
		return VMcmd
			
	def writeLHS( self, seg_ind, a_index ) :
		if not '' == a_index :		# meaning this is an array
			VMcmd = self.writePushPop( 'push' , seg_ind )
			VMcmd += a_index
			VMcmd += self.writeArrayElem( True )
		else :
			VMcmd = 'pop ' + seg_ind + "\n"
		return VMcmd
		
	def writeConst( self, value ) :
		if( 'this' == value ) :
			return "push pointer 0\n"
		elif( 'true' == value ) :
			return "push constant 1\n" + "neg\n"
		elif( value in ['null', 'false'] ) :
			return "push constant 0\n"
		
		

			
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
	[buf, state, VMcmds, numM] = j_analyzer.analyze('class' , 1 )
	j_analyzer.Write( buf )
	j_analyzer.WriteVM( re.sub( r"\n+" , r"\n", VMcmds , flags=re.MULTILINE)  )


		






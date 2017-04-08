
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
			
	def commandType( self ) :
# return : C_ARITHMETIC, C_PUSH, C_POP, C_LABEL, C_GOTO, C_IF, C_FUNCTION, C_RETURN, C_CALL
		if( re.search( "add|sub|neg|gt|lt|eq|and|or|not" , self.instr ) ) :
			return "C_ARITHMETIC"
		elif( "push" == self.instr ) :
			return "C_PUSH"
		elif( "pop" == self.instr ) :
			return "C_POP"
		elif( "goto" == self.instr ) :
			return "C_GOTO"
		elif( "if-goto" == self.instr ) :
			return "C_IF"
		elif( "label" == self.instr ) :
			return "C_LABEL"
		elif( "function" == self.instr ) :
			return "C_FUNCTION"
		elif( "return" == self.instr ) :
			return "C_RETURN"
		elif( "call" == self.instr ) :
			return "C_CALL"
		else :
			return "C_UNDEF"
	
	def arg1( self, command ) :
		if( "C_ARITHMETIC" == command ) :
			return self.instr
		else :
			return self.args1
			
	
	# this is being used for the "index" argument of writePushPop
	def arg2( self, command ) :
		if( re.match( "C_P|C_FUNCTION|C_CALL" , command) ) :
			if "static" == self.args1 :
				return self.base + '.' + self.args2		# is what produces filename.i
			else :
				return self.args2
		
class CodeWriter():
	def __init__( self, outfile):
		self.outstream = open( outfile, "w")
		self.num_jmps = 1;	# used to keep track of gt,lt,eq which require labels - and hence unique IDs :(
	# in the case of eq, gt, lt, you'll have to hit WR_TRUE_ and DONE_ to uniquify
		self.num_calls = 1;
		self.num_rets = 1;
		self.snippets = {}
		self.snippets['push' ] = self.push
		self.snippets['pop'] = self.pop
		self.snippets['add'] = self.add
		self.snippets['sub'] = self.sub
		self.snippets['not'] = self.c_not
		self.snippets['and'] = self.c_and
		self.snippets['or'] = self.c_or
		self.snippets['neg'] = self.neg
		self.segs = {'local' : "LCL", 'argument' : "ARG" ,  'this' : "THIS" , 'that' : "THAT"}


	def writeArith( self, command ) :
#		pdb.set_trace()
		match = re.search( "add|sub|neg|and|or|not", command )
		if match :
			self.outstream.write( '// ' + match.group(0) )
			self.outstream.write( textwrap.dedent( self.snippets[ match.group(0) ] ) )
			return
		match = re.search( "gt|lt|eq", command )
		if match :
			self.outstream.write( '// ' + match.group(0) )
			dump = re.sub( r"JCOMP" , "J" + match.group(0).upper(), self.comp )
			dump = re.sub( r"(?P<tag>WR_TRUE_|DONE_)" , r"\g<tag>" + str(self.num_jmps), dump, )
			self.num_jmps = self.num_jmps + 1
			self.outstream.write( textwrap.dedent( dump ) )

	def writePushPop( self, command, segment, index ) :
	# we know that in the case of push constant i, segment is meaningless and we just push i onto stack
	# 4 cases : local, argument, this, that
	#		  : pointer, temp pointer 0 is this = R3, that = R4, temp1 = R5; temp 0 => R5
	#		  : constant - a virtual segment -- only meaningful for push commands
	#		  : static : when you encounter push static i in foo.vm --> 
	#		  : 			@foo.i ; D=M; then push D onto stack
		if "C_PUSH" == command :
			match = re.search( "local|argument|this|that", segment )
			self.outstream.write( '// ' + 'push ' + segment + ' ' + index )		# will be a mess for static :)
			if match :
				dump = re.sub( r"segment", self.segs[segment], self.def_seg_push )
				dump = re.sub( r"offset" , index , dump)
				self.outstream.write( textwrap.dedent( dump + self.push ) )
			elif "constant" == segment :
				dump = re.sub( r"constval", index, self.def_const )
				self.outstream.write( textwrap.dedent( dump + self.push ) )
			elif "static" == segment :
				dump = re.sub( r"static", index, self.def_static )	# index is guaranteed to be filename.i
				self.outstream.write( textwrap.dedent( dump + self.push) )
			elif "pointer" == segment :
				label = "R" + str( 3 + int( index ) )		# not the most efficient machine code - could optimize
				dump = re.sub( r"static" , label, self.def_static )
				self.outstream.write( textwrap.dedent( dump + self.push) )
			elif "temp" == segment :					# definitely can refactor for elegance
				label = "R" + str( 5 + int( index ) )		# same comment on efficiency..
				dump = re.sub( r"static" , label, self.def_static )
				self.outstream.write( textwrap.dedent( dump + self.push) )
				
			
		if "C_POP" == command :
#			pdb.set_trace()
			match = re.search( "local|argument|this|that", segment )
			self.outstream.write( '// ' + 'pop ' + segment + ' ' + index )	# static will be a mess here..
			if match :
				dump = re.sub( r"segment", self.segs[segment], self.def_seg_pop )
				dump = re.sub( r"offset" , index , dump)
				self.outstream.write( textwrap.dedent( dump + self.pop ) )
			elif "static" == segment :
			# we want pop static i in foo.vm to update the variable foo.i in foo.asm
				dump = re.sub( r"static", index, self.def_pop_static )	# index is guaranteed to be filename.i
				self.outstream.write( textwrap.dedent( dump + self.pop) )
			elif "pointer" == segment :
				label = "R" + str( 3 + int( index ) )
				dump = re.sub( r"static" , label, self.def_pop_static )
				self.outstream.write( textwrap.dedent( dump + self.pop) )
			elif "temp" == segment :
				label = "R" + str( 5 + int( index ) )
				dump = re.sub( r"static" , label, self.def_pop_static )
				self.outstream.write( textwrap.dedent( dump + self.pop) )

	def writeGoto( self,  segment ) :
		self.outstream.write( '//  goto ' + segment + "\n")
		self.outstream.write( '@' + segment + "\n" + '0, JMP' + "\n" )
		
	def writeIf( self,  segment ) :
		self.outstream.write( '// if-goto ' + segment )
		self.outstream.write( textwrap.dedent( re.sub( r"label" , segment, self.def_if_goto ) ) )

	def writeLabel( self,  segment ) :
		self.outstream.write( '// label ' + segment + "\n" + '(' + segment + ")\n")	
			
	def writeCall( self,  functionName, nArgs ) :
		# call functionName nArgs
		self.outstream.write( '// return ' )
		dump = re.sub( r"(?P<tag>returnAddress" , r"\g<tag>_" + str( self.num_rets), dump )
		self.num_rets = self.num_rets + 1
		self.outstream.write( textwrap.dedent( dump) )
			
	def Close( self ) :
		self.outstream.close();

	def_call = """
	@returnAddress
	D = A
	@SP
	AM = M+1
	A = A-1
	M = D
	@LCL
	D = M
	@SP
	AM = M+1
	A = A-1
	M = D		
	@ARG
	@LCL
	D = M
	@SP
	AM = M+1
	A = A-1
	M = D
	@THIS
	D = M
	@SP
	AM = M+1
	A = A-1
	M = D
	@THAT
	D = M
	@SP
	AM = M+1
	A = A-1
	M = D
	@m5mNargs
	D = A
	@SP
	D = A - D
	@ARG
	M = D
	@SP
	D = A
	@LCL
	M = D
	@functionName
	0,JMP
	(returnAddress)
	"""


	def_if_goto = """
	@SP
	AM = M - 1
	D = M
	@label
	D, JNE
	"""
		
	def_seg_pop = """
	@offset
	D = A
	@segment
	D = M + D
	"""

	def_seg_push = """
	@offset
	D = A
	@segment
	A = M + D
	D = M
	"""
	
	def_const = """
	@constval
	D = A
	"""
	
	def_static = """
	@static
	D = M
	"""

	
	# you have to define segment first with D containing the address value
	push = 	"""
	@SP
	AM = M + 1
	A = A - 1
	M = D
	"""


	def_pop_static = """
	@static
	D = A
	"""
	
	# need to have D containing target address
	pop = """
	@R13
	M = D
	@SP
	AM = M - 1
	D = M
	@R13
	A = M
	M = D
	"""

	add = """
	@SP
	AM = M - 1
	D = M
	A = A - 1
	M = M + D
	"""
	
	sub = """
	@SP
	AM = M - 1
	D = M
	A = A - 1
	M = M - D
	"""
	
	c_and =	"""
	@SP
	AM = M - 1
	D = M
	A = A - 1
	M = M & D
	"""
	
	c_or = """
	@SP
	AM = M - 1
	D = M
	A = A - 1
	M = M | D
	"""
	
	c_not = """
	@SP
	A = M - 1
	M = !M
	"""
	
	neg = """
	@SP
	A = M - 1
	M = -M
	"""
	
	# need to hit JCOMP based on gt, lt, eq and also add # to WR_TRUE_ and DONE_
	comp = """
	@SP
	AM = M - 1
	D = M
	A = A - 1
	D = M - D
	@WR_TRUE_
	D, JCOMP
	@SP
	A = M - 1
	M = 0
	@DONE_
	0, JMP
	(WR_TRUE_)
	@SP
	A = M - 1
	M = -1
	(DONE_)
	"""

# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/Adder.asm

# if no files in the specified source, then die..

source = sys.argv[1]
# pdb.set_trace()	
	
if os.path.isdir( source ) :
	# start off writing to source/source.asm by processing every .vm file you encounter
	filelist = os.popen( "ls " + source + "/*.vm").read().split()
	if len( filelist ) < 1 :
		print( "Please check if the directory has .vm files in it" )
	else :
		target = source + "/" + re.sub( r".+?/?([^/]+)/*$", r"\1" , source ) + '.asm'
else :
	filelist = [source]
	target = re.sub( "\.vm" , ".asm" , source )

	
vm_codewr = CodeWriter( target )

for file in filelist :
	vm_parser = Parser( file )

	while vm_parser.hasMoreCommands():
		vm_parser.advance()
		print( vm_parser.instr)
		cType = vm_parser.commandType()
		if "C_ARITHMETIC" == cType :
			vm_codewr.writeArith( vm_parser.arg1(cType) )
		elif re.match( "C_P" , cType ) :		# push or pop command..
			vm_codewr.writePushPop( cType, vm_parser.arg1(cType) , vm_parser.arg2(cType) )
		elif re.match( "C_GOTO" , cType ) :
			vm_codewr.writeGoto(  vm_parser.arg1(cType) )
		elif re.match( "C_IF" , cType ) :
			vm_codewr.writeIf( vm_parser.arg1(cType) )
		elif re.match( "C_LABEL" , cType ) :
#			pdb.set_trace()
			vm_codewr.writeLabel( vm_parser.arg1(cType) )
		

vm_codewr.Close()

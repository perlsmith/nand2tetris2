
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
		match = re.match( "([\\/]+)\.vm" , filename )		# dir1\dir2\name.vm --> name is what we capture
		base = match.group(1)
		
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
			self.args2 = self.command[2]
			
	def commandType( self ) :
# return : C_ARITHMETIC, C_PUSH, C_POP, C_LABEL, C_GOTO, C_IF, C_FUNCTION, C_RETURN, C_CALL
		if( re.search( "add|sub|neg|gt|lt|eq|and|or|not" , self.instr ) ) :
			return "C_ARITHMETIC"
		elif( "push" == self.instr ) :
			return "C_PUSH"
		elif( "pop" == self.instr ) :
			return "C_POP"
		else :
			return "C_UNDEF"
	
	def arg1( self, command ) :
		if( "C_ARITHMETIC" == command ) :
			return self.instr
		elif( re.match( "C_P", command ) ) :
			return self.args1
	
	def arg2( self, command ) :
		if( re.match( "C_P|C_FUNCTION|C_CALL" , command) ) :
			if "static" == self.args1 :
				return self.base + '.' + self.args2
			else :
				return self.args2
		
class CodeWriter():
	def __init__( self, outfile):
		self.outstream = open( outfile, "w")
		self.num_jmps = 1;	# used to keep track of gt,lt,eq which require labels - and hence unique IDs :(
	# in the case of eq, gt, lt, you'll have to hit WR_TRUE_ and DONE_ to uniquify
		self.snippets = {}
		self.snippets['push' ] = self.push
		self.snippets['pop'] = self.pop
		self.snippets['add'] = self.add
		self.snippets['sub'] = self.sub
		self.snippets['not'] = self.c_not
		self.snippets['and'] = self.c_and
		self.snippets['or'] = self.c_or
		self.snippets['neg'] = self.neg
		self.segs = {'local' : "LCL", 'argument' : "ARG" ,  'this' : "" , 'that' : "THAT"}


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
				dump = re.sub( r"segment", self.segs[segment], self.def_seg )
				dump = re.sub( r"offset" , index , dump)
				self.outstream.write( textwrap.dedent( dump + self.load_D + self.push ) )
			elif "constant" == segment :
				dump = re.sub( r"constval", index, self.def_const )
				self.outstream.write( textwrap.dedent( dump + self.push ) )
			elif "static" == segment :
				dump = re.sub( r"static", index, self.def_static )	# index is guaranteed to be filename.i
				self.outstream.write( textwrap.dedent( dump + self.push) )
			elif "pointer" == segment :
				label = "R" + str( 3 + int( index ) )
				dump = re.sub( r"static" , label, def_static )
			elif "temp" == segment :
				label = "R" + str( 5 + int( index ) )
				dump = re.sub( r"static" , label, def_static )
				
			
#		if "C_POP" == command :
			match = re.search( "local|argument|this|that", segment )
			self.outstream.write( '// ' + 'pop ' + segment + ' ' + index )	# static will be a mess here..
			if match :
				
			
			
	def Close( self ) :
		self.outstream.close();
	
	def_seg = """
	@segment
	D = A
	@offset
	A = D + A
	"""

	def_const = """
	@constval
	D = A
	"""
	
	def_static = """
	@static
	D = M
	"""
	
	load_D = "D = M"
	
	# you have to define segment first
	push = 	"""
	@SP
	AM = M + 1
	A = A - 1
	M = D
	"""

	# good only for LCL, ARG, THIS, THAT
	pop = """
	@offset
	D = A
	@segment
	D = A + D
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
	M = 0
	@DONE_
	0, JMP
	(WR_TRUE_)
	@SP
	M=1
	(DONE_)
	"""

# Main program :

# if a directory "Adder" is input containing .vm files, then the output is Adder/Adder.asm

# if no files in the specified source, then die..

source = sys.argv[1]

if os.path.isdir( source ) :
	# start off writing to source/source.asm by processing every .vm file you encounter
	filelist = os.popen( "ls *.vm 2> nul")
	if len( filelist ) < 1 :
		print "Please check if the directory has .vm files in it"
	else :
		target = source + '.asm'
else :
	filelist = [source]
	target = re.sub( "\.vm" , ".asm" , source )

vm_parser = Parser( sys.argv[1] )
vm_codewr = CodeWriter( re.sub( ".vm" , ".asm", sys.argv[1] ) )

while vm_parser.hasMoreCommands():
	vm_parser.advance()
	print( vm_parser.instr)
#	pdb.set_trace()	
	cType = vm_parser.commandType()
	if "C_ARITHMETIC" == cType :
		vm_codewr.writeArith( vm_parser.arg1(cType) )
	elif re.match( "C_P" , cType ) :		# push or pop command..
		vm_codewr.writePushPop( cType, vm_parser.arg1(cType) , vm_parser.arg2(cType) )

vm_codewr.Close()

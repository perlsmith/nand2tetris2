
import sys
import re
import pdb

class Parser():
	def __init__( self, filename ):
		print( "Parser constructor called")
		self.instream = open( filename, "r")
		
	def hasMoreCommands( self ):
#		pdb.set_trace()
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
			self.arg1 = self.command[1]
			self.arg2 = self.command[2]
		
class CodeWriter():
	def __init__( self, outfile):
		print( "CodeWriter called")
		self.outstream = open( outfile, "w")
	
	
		

		
vm_parser = Parser( sys.argv[1] )

while vm_parser.hasMoreCommands():
	vm_parser.advance()
	print( vm_parser.instr)
// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Put your code here.

// hack got no mult, so obviously it's repeated addition - for loop
// most efficient alkorezm will use the smaller number for the loop

// find smaller number here
	@R2
	M=0			// null this out
	@R0
	D=M
	@counter
	M=D			// until we find that R1 is smaller
	@R1		// now store R1 in R2
	D=M
	@R2
	M=D
	@R0		// now we compareth
	D=M-D
	@R1SMALLER
	D, JGT		// if R1 is smaller than R0, this will be > 0 ..
	@BEGIN
	0, JMP			// start multiplying

(R1SMALLER)
	@R1
	D=M
	@counter
	M=D
	@R0
	D=M
	@R2
	M=D

(BEGIN)
	@R2		// which has the larger number
	D=M
	@larger
	M=D		// readability only - could have simply used R0 or R1 to reduce footprint
	
// for loop here
(LOOP)
	@counter
	MD=M-1
	@END
	D, JEQ		// if we're at 0, we're done mate
				// else
	@larger
	D=M
	@R2
	M=D+M
	@LOOP
	0, JMP
	
(END)
	@END
	0, JMP

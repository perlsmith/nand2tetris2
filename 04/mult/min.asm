// finds min of R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// how : start off assuming R0 is smaller. Then, subtract R1 from R0 and, if 
// result is > 0 => R1 is smaller, put R1 in R2.

	@R0
	D=M
	@R2
	M=D			// until we find that R1 is smaller
	@R1		
	D=M
	@R0
	M=M-D		// we have R0 - R1
	@R0			// if > 0, then we need to put R1 in R2
	D=M
	@R1SMALLER
	D, JGT		// if R1 is smaller than R0, this will be > 0 ..
	@END
	0, JMP		// else, we're done

(R1SMALLER)
	@R1
	D=M
	@R2
	M=D

(END)
	@END
	0, JMP

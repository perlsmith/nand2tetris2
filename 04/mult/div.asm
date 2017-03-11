// Divides R0 by R1 and stores the dividend in R2 and remainder in R3
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

	@R2
	M = 0
	@R3
	M = 0
	@R0
	D = M
	@END
	D, JEQ
	@store
	M = D		// store to restore
(LOOP)
	@R1
	D = D - M
	@REMAINDER
	D, JLT
	@R2
	M = M + 1
	@EVENLY
	D, JEQ	
	@LOOP
	0, JMP
	
(REMAINDER)
	@R1
	D = D + M
	@R3
	M = D
(EVENLY)
	@store
	D = M
	@R0
	M = D
	
(END)
	@END
	0, JMP

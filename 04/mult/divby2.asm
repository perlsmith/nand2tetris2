// Divides R0 by 2 and stores the dividend in R1 and remainder in R2
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// how : counter goes from 2 to 32768 ( doubling each time )
// start with 1 and dump result of the AND in R2
// start off setting R1 to 0 and after that, based on result of the AND of
// counter with R0, you either OR R1 with counter or do nothing

	@R1
	M = 0
	D = 1
	@R0
	D = M & D
	@R2
	M = D		// remainder captured
	@lagcount
	M = 1
	@2
	D = A
	@counter
	M = D
	
(LOOP)
	@R0
	D = M & D	// we're expecting D (pre) to already have the counter value based on knowing our code
	@NO_ACTION
	D, JEQ
	@lagcount	// else, we need to OR R1 with the lagging counter
	D = M
	@R1
	M = M | D
(NO_ACTION)
	@16384		// can only load a 15 bit number :)
	D = A
	D = D + A
	@counter
	D = M - D
	@END
	D, JEQ
				// else, we need to double counter and double lagcount
	@lagcount
	D = M
	M = M + D
	@counter
	D = M
	MD = M + D

	@LOOP
	0, JMP
	
(END)
	@END
	0, JMP

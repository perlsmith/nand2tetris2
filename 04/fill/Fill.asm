// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Put your code here.

(POLL_WHILE_CLEAR)
	@KBD
	D=M
	@POLL_WHILE_CLEAR
	D, JEQ
				// not zero implies a key pressed
	@pix_val
	M=-1
	@PAINT
	0, JMP

(POLL_WHILE_BLACK)
	@KBD
	D=M
	@POLL_WHILE_BLACK
	D, JNE
				// else, zero implies no key pressed anymore, so clear the screen
	@pix_val
	M=0
	@PAINT
	0, JMP
	
(PAINT)
	@8192
	D=A
	@counter
	M=D
(LOOP_DRAW)
	@counter
	MD=M-1
	@DRAW_DONE
	D, JEQ		// if we're 0, we're done
	@SCREEN
	D=A
	@counter
	D=M+D		// finally the word we're going to be writing to..
	@scr_pointer
	M=D
	@pix_val
	D=M
	@scr_pointer
	A=M
	M=D
	@LOOP_DRAW
(DRAW_DONE)
	@pix_val
	D=M
	@POLL_WHILE_CLEAR
	D, JEQ		// if you were writing 0's then you just cleared the screeen..
	@POLL_WHILE_BLACK
	D, JMP

(END)
	@END
	0, JMP
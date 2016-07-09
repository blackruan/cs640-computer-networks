all: blaster blastee

blaster: blaster.o
	gcc -ggdb3 -lpthread -lm blaster.o -o blaster

blastee: blastee.o
	gcc -ggdb3 blastee.o -o blastee

blaster.o: blaster.c
	gcc -ggdb3 -c blaster.c

blastee.o: blastee.c
	gcc -ggdb3 -c blastee.c

clean:
	rm -rf *o blaster blastee

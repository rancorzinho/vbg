CFLAGS=-lX11 -lXtst -pedantic

all: write_cmd.c
	cc $(CFLAGS) write_cmd.c -o write_cmd
run: write_cmd
	./vbg.py -m cmd
clean:
	rm -f write_cmd *.pyc


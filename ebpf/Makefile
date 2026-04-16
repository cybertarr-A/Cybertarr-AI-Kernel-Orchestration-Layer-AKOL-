CLANG ?= clang
ARCH := $(shell uname -m)
CFLAGS := -O2 -g -Wall -target bpf
INCLUDES := -I/usr/include/$(ARCH)-linux-gnu

all: spike_kern.o

spike_kern.o: spike_kern.c cybertarr_common.h
	$(CLANG) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f spike_kern.o

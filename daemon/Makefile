CC ?= gcc
CFLAGS := -O2 -g -Wall
LDFLAGS := -lbpf -lelf -lz -lpthread

SRCS := spike_user.c controller.c scheduler.c
OBJS := $(SRCS:.c=.o)
TARGET := cybertarr-daemon

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c daemon.h ../ebpf/cybertarr_common.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

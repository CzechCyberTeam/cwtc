CC = g++
CFLAGS = -Wall -Wextra -pedantic -std=c++11

PROGRAM = sbx
SOURCES = sbx.cpp

all: $(PROGRAM)

$(PROGRAM): $(SOURCES)
	$(CC) $(CFLAGS) $(SOURCES) -o $(PROGRAM)

clean:
	rm -f $(PROGRAM)

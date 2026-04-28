CC      = gcc
CFLAGS  = -O2 -Wall -Wextra -std=c11
LDFLAGS = -lm
TARGET  = uptime-kernel

# ARM64 크로스 컴파일 (aarch64-linux-gnu-gcc 필요)
CC_ARM  = aarch64-linux-gnu-gcc

.PHONY: all arm clean install

all:
	$(CC) $(CFLAGS) -o $(TARGET) uptime_kernel.c $(LDFLAGS)
	@echo "✅ Built: $(TARGET)"

arm:
	$(CC_ARM) $(CFLAGS) -static -o $(TARGET)-arm64 uptime_kernel.c $(LDFLAGS)
	@echo "✅ Built ARM64: $(TARGET)-arm64"

install: all
	install -m 755 $(TARGET) /usr/local/bin/$(TARGET)
	@echo "✅ Installed to /usr/local/bin/$(TARGET)"

clean:
	rm -f $(TARGET) $(TARGET)-arm64

test: all
	./$(TARGET)

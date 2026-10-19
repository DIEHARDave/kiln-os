# Build against a linux-5.10.186 tree prepared by setup.sh:
#   make KDIR=/path/linux-5.10.186
KDIR ?= $(HOME)/workspace/chainload-build/linux-5.10.186
CROSS_COMPILE ?= mipsel-linux-

obj-m := chainload.o
chainload-y := chainload_main.o tramp.o

all:
	cp -f $(CURDIR)/chainload.c $(CURDIR)/chainload_main.c
	$(MAKE) -C $(KDIR) ARCH=mips CROSS_COMPILE=$(CROSS_COMPILE) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) ARCH=mips CROSS_COMPILE=$(CROSS_COMPILE) M=$(CURDIR) clean
	rm -f chainload_main.c

.PHONY: all, print, clean

TARGET=test

SRC_PATH := src
INC_PATH := inc
OBJSDIR  := build

SRCS+= $(foreach x, $(SRC_PATH), $(wildcard $(addprefix $(x)/*,.cpp*)))
OBJS += $(addprefix $(OBJSDIR)/, $(addsuffix .o, $(notdir $(basename $(SRCS)))))

CXXFLAGS += -I./$(INC_PATH) -DDEBUG -Wall -g
LDFLAGS += -L./lib -lm

CXX:= g++

all: mkdir ${TARGET}
	@echo Build complete!

${TARGET}: $(OBJS)
	@echo " [LINK] $@"
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)

$(OBJSDIR)/%.o: $(SRC_PATH)/%.cpp
	@echo " [CXX]  $@"
	$(CXX) -c $< -o $@ $(CXXFLAGS)

mkdir:
	@mkdir -p $(OBJSDIR)

print:
	@echo $(OBJS)

clean:
	rm -rf ${OBJSDIR}
	rm -rf ${TARGET}

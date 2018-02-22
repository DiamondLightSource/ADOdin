TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

CXXFLAGS += -std=c++0x

CXXFLAGS += -O0

LIBRARY_IOC = odinDetector

LIB_SRCS += odinDetector.cpp odinDataDriver.cpp OdinClient.cpp odinRestApi.cpp odinDetectorRestApi.cpp odinDataRestApi.cpp

LIB_LIBS += restClient

DBD += odinDetectorSupport.dbd

include $(ADCORE)/ADApp/commonLibraryMakefile

#=============================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

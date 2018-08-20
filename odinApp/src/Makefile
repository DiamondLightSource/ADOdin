TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

CXXFLAGS += -O0

LIBRARY_IOC = OdinDetector

LIB_SRCS += OdinDetector.cpp OdinDataDriver.cpp OdinClient.cpp OdinRestApi.cpp OdinDetectorRestApi.cpp OdinDataRestApi.cpp

LIB_LIBS += restClient

DBD += OdinDetectorSupport.dbd

include $(ADCORE)/ADApp/commonLibraryMakefile

#=============================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

TOP = ../..
include $(TOP)/configure/CONFIG

PROD_IOC = xspress
DBD += xspress.dbd
xspress_DBD += base.dbd
xspress_DBD += asyn.dbd
xspress_DBD += busySupport.dbd
xspress_DBD += ADSupport.dbd
xspress_DBD += NDPluginSupport.dbd
xspress_DBD += NDFileHDF5.dbd
xspress_DBD += NDFileJPEG.dbd
xspress_DBD += NDFileTIFF.dbd
xspress_DBD += NDFileNull.dbd
xspress_DBD += NDPosPlugin.dbd
xspress_DBD += calcSupport.dbd
xspress_DBD += OdinDetectorSupport.dbd
xspress_DBD += OdinDetectorSupport.dbd
xspress_SRCS += xspress_registerRecordDeviceDriver.cpp
xspress_LIBS += OdinDetector
xspress_LIBS += OdinDetector
xspress_LIBS += frozen
xspress_LIBS += restClient
xspress_LIBS += calc
xspress_LIBS += NDPlugin
xspress_LIBS += ADBase
xspress_LIBS += cbfad
xspress_LIBS += busy
xspress_LIBS += asyn
xspress_LIBS += $(EPICS_BASE_IOC_LIBS)
xspress_SRCS += xspressMain.cpp

include $(TOP)/configure/RULES


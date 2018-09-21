cmake_minimum_required(VERSION 3.5)
project(ADOdin_dev)

set(EPICS_BASE "/dls_sw/epics/R3.14.12.3/base")
set(SUPPORT "/dls_sw/prod/R3.14.12.3/support")
set(EXCALIBURDETECTOR "/dls_sw/work/tools/RHEL6-x86_64/odin/excalibur-detector")
set(EIGERDETECTOR "/dls_sw/work/tools/RHEL6-x86_64/eiger-detector")
set(ODINDATA "/dls_sw/work/tools/RHEL6-x86_64/odin/mef65357/odin-data")
set(TOOLS "/dls_sw/prod/tools/RHEL6-x86_64")
set(ADCORE "${SUPPORT}/ADCore/2-6dls6")
set(RESTCLIENT "${SUPPORT}/restClient/0-1")
set(ASYN "${SUPPORT}/asyn/4-31")
set(CALC "${SUPPORT}/calc/3-1")

include_directories(
    ${ADCORE}/include
    ${RESTCLIENT}/include
    ${EPICS_BASE}/include
    ${SUPPORT}/include
    ${EXCALIBURDETECTOR}/include
    ${ASYN}/include
    ${EIGERDETECTOR}/include
    ${ODINDATA}/include
    ${CALC}/include
    ${TOOLS}/include
    ${EPICS_BASE}/include/os/Linux)

set(ADODIN_DEV_SOURCE_FILES
    etc/makeIocs/O.Common/excalibur/excaliburApp/src/excaliburMain.cpp
    etc/makeIocs/O.Common/eiger/eigerApp/src/eigerMain.cpp
    iocs/excalibur/excaliburApp/src/excaliburMain.cpp
    iocs/excalibur/excaliburApp/src/O.linux-x86_64/excalibur_registerRecordDeviceDriver.cpp
    iocs/eiger/eigerApp/src/eigerMain.cpp
    odinApp/src/OdinClient.cpp
    odinApp/src/OdinClient.h
    odinApp/src/OdinRestApi.h
    odinApp/src/OdinRestApi.cpp
    odinApp/src/OdinDetectorRestApi.h
    odinApp/src/OdinDetectorRestApi.cpp
    odinApp/src/OdinDetector.h
    odinApp/src/OdinDetector.cpp
    odinApp/src/OdinDataRestApi.h
    odinApp/src/OdinDataRestApi.cpp
    odinApp/src/OdinDataDriver.h
    odinApp/src/OdinDataDriver.cpp
    odinApp/src/OdinDataConfig.h
    cmake-build-debug/CMakeFiles/feature_tests.c
    cmake-build-debug/CMakeFiles/3.10.3/CompilerIdC/CMakeCCompilerId.c
    cmake-build-debug/CMakeFiles/3.10.3/CompilerIdCXX/CMakeCXXCompilerId.cpp
)

add_library(ADOdin_dev_source ${ADODIN_DEV_SOURCE_FILES})
add_custom_target(ADOdin_dev_build
    COMMAND $(MAKE) -C /dls_sw/work/R3.14.12.3/support/ADOdin_dev
    SOURCES ${ADODIN_DEV_SOURCE_FILES})

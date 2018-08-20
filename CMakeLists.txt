cmake_minimum_required(VERSION 3.5)
project(ADOdin)

set(SCRATCH "/scratch/work/R3.14.12.3/support")
set(SUPPORT "/dls_sw/prod/R3.14.12.3/support")
set(WORK "/dls_sw/work/R3.14.12.3/support")
set(EPICS_BASE "/dls_sw/epics/R3.14.12.3/base")
set(RESTCLIENT "${SCRATCH}/restClient")
set(ASYN "${SUPPORT}/asyn/4-31")
set(ADSIMDETECTOR "${SUPPORT}/ADSimDetector/1-2")
set(ADCORE "${SUPPORT}/ADCore/2-6dls1")

include_directories(
    ${RESTCLIENT}/include
    ${SCRATCH}/include
    ${SUPPORT}/include
    ${WORK}/include
    ${ASYN}/include
    ${ADSIMDETECTOR}/include
    ${EPICS_BASE}/include
    ${ADCORE}/include
    ${EPICS_BASE}/include/os/Linux)

set(ADODIN_SOURCE_FILES
    odinApp/src/OdinRestApi.cpp
    odinApp/src/OdinRestApi.h
    odinApp/src/OdinDetectorRestApi.h
    odinApp/src/OdinDetectorRestApi.cpp
    odinApp/src/OdinDetector.h
    odinApp/src/OdinDataDriver.h
    odinApp/src/OdinClient.cpp
    odinApp/src/OdinDetector.cpp
    odinApp/src/OdinClient.h
    odinApp/src/OdinDataConfig.h
    odinApp/src/OdinDataDriver.cpp
    odinApp/src/OdinDataRestApi.h
    odinApp/src/OdinDataRestApi.cpp
)

add_library(ADOdin_source ${ADODIN_SOURCE_FILES})
add_custom_target(ADOdin_build
    COMMAND $(MAKE) -C /scratch/work/R3.14.12.3/support/ADOdin
    SOURCES ${ADODIN_SOURCE_FILES})

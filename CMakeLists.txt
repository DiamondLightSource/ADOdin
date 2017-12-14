cmake_minimum_required(VERSION 3.5)
project(ADOdin)

set(SCRATCH "/scratch/work/R3.14.12.3/support")
set(SUPPORT "/dls_sw/prod/R3.14.12.3/support")
set(WORK "/dls_sw/work/R3.14.12.3/support")
set(EPICS_BASE "/dls_sw/epics/R3.14.12.3/base")
set(ADCORE "${SUPPORT}/ADCore/2-6dls1")
set(RESTCLIENT "${SCRATCH}/restClient")
set(ASYN "${SUPPORT}/asyn/4-31")
set(ADSIMDETECTOR "${SUPPORT}/ADSimDetector/1-2")

include_directories(
    ${ADCORE}/include
    ${RESTCLIENT}/include
    ${SCRATCH}/include
    ${SUPPORT}/include
    ${WORK}/include
    ${ASYN}/include
    ${ADSIMDETECTOR}/include
    ${EPICS_BASE}/include
    ${EPICS_BASE}/include/os/Linux
    odinApp/frozenSrc)

set(ADODIN_SOURCE_FILES
    odinApp/frozenSrc/frozen.c
    odinApp/frozenSrc/frozen.h
    odinApp/src/odinRestApi.cpp
    odinApp/src/odinRestApi.h
    odinApp/src/odinDetector.h
    odinApp/src/odinDetector.cpp
    cmake-build-debug/CMakeFiles/feature_tests.c
    cmake-build-debug/CMakeFiles/3.8.2/CompilerIdC/CMakeCCompilerId.c
    cmake-build-debug/CMakeFiles/3.8.2/CompilerIdCXX/CMakeCXXCompilerId.cpp
    iocs/example/exampleApp/src/exampleMain.cpp
    iocs/example/exampleApp/src/O.linux-x86_64/example_registerRecordDeviceDriver.cpp
)

add_library(ADOdin_source ${ADODIN_SOURCE_FILES})
add_custom_target(ADOdin_build
    COMMAND $(MAKE) -C /scratch/work/R3.14.12.3/support/ADOdin
    SOURCES ${ADODIN_SOURCE_FILES})

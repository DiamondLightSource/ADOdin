epicsEnvSet "EPICS_CA_MAX_ARRAY_BYTES", '7000000'
epicsEnvSet "EPICS_TS_MIN_WEST", '0'

epicsEnvSet "INSTALL_DIR", "/odin/epics/support/ADOdin/iocs/xspress"

# Device initialisation
# ---------------------

dbLoadDatabase "$(INSTALL_DIR)/dbd/xspress.dbd"
xspress_registerRecordDeviceDriver(pdbbase)

callbackSetQueueSize(400000)

# odinDataDriverConfig(const char * portName, const char * serverPort, int odinServerPort, int odinDataCount, const char * datasetName, const char * detectorName, int maxBuffers, size_t maxMemory)
odinDataDriverConfig("ODN.OD", "127.0.0.1", 8888, 2, "data", "xspress", 0, 0)

# odinDetectorConfig(const char * portName, const char * serverPort, int odinServerPort, const char * detectorName, int maxBuffers, size_t maxMemory, int priority, int stackSize)
odinDetectorConfig("ODN.CAM", "127.0.0.1", 8888, "xspress", 0, 0)

# NDStdArraysConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)
NDStdArraysConfigure("ODN.ARR", 100, 0, "ODN.CAM", 0, 0, 0, 0, 0, 1)

# Final ioc initialisation
# ------------------------
dbLoadRecords '$(INSTALL_DIR)/db/xspress_expanded.db'
iocInit

dbpf "XSPRESS:OD:ReadStatus.SCAN", "7"

dbpf "XSPRESS:CAM:ReadStatus.SCAN", "7"

dbpf "XSPRESS:CAM:LiveViewEndpoint", "tcp://127.0.0.1:15510"

# TODO: check if this is required as also in odin_server.cfg with different path
# dbpf "XSPRESS:CAM:CONFIG_PATH", "/home/xspress3/xspress3_settings/current"

# TODO: tidy up below commands before release
# -------------------------------------------
dbpf "XSPRESS:CAM:RUN_FLAGS", "2"
dbpf "XSPRESS:CAM:TriggerMode", "2"

dbpf "XSPRESS:OD:FilePath", "/data/odin-testing"
dbpf "XSPRESS:OD:FileName", "test.hdf5"
# -------------------------------------------

dbpf "XSPRESS:CAM:RECONFIGURE", "1"

# -------------------------------------------
# Odin PVs which can be lost from reconfigure
# -------------------------------------------
dbpf "XSPRESS:OD:ImageHeight", "1"
dbpf "XSPRESS:OD:ImageWidth", "4096"
dbpf "XSPRESS:OD:NumFramesChunks", "1"
dbpf "XSPRESS:OD:NumRowChunks", "1"
dbpf "XSPRESS:OD:NumColChunks", "4096"

# -------------------------------------------
# Enable NDStdArrays callbacks for live view
# -------------------------------------------
dbpf "XSPRESS:ARR:EnableCallbacks", "Enable"

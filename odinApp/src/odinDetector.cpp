#include "odinDetector.h"

#include <sstream>

#include <epicsExport.h>
#include <epicsString.h>
#include <iocsh.h>
#include <drvSup.h>

static const std::string DRIVER_VERSION("0-1");
static const char *driverName = "OdinDetector";

// These parameters are optionally configured by ioc init commands
std::string      OdinDetector::mOdinDataLibraryPath = "";
std::string      OdinDetector::mIPAddress           = "";
int              OdinDetector::mReadyPort           =  0;
int              OdinDetector::mReleasePort         =  0;
int              OdinDetector::mMetaPort            =  0;
std::string      OdinDetector::mProcessPluginName   = "";
std::string      OdinDetector::mDetectorLibraryPath = "";

/* Constructor for Odin driver; most parameters are simply passed to ADDriver::ADDriver.
 * After calling the base class constructor this method creates a thread to collect the detector
 * data, and sets reasonable default values for the parameters defined in this class,
 * asynNDArrayDriver, and ADDriver.
 * \param[in] portName The name of the asyn port driver to be created.
 * \param[in] serverHostname The IP or url of the detector webserver.
 * \param[in] maxBuffers The maximum number of NDArray buffers that the
 *            NDArrayPool for this driver is allowed to allocate. Set this to
 *            -1 to allow an unlimited number of buffers.
 * \param[in] maxMemory The maximum amount of memory that the NDArrayPool for
 *            this driver is allowed to allocate. Set this to -1 to allow an
 *            unlimited amount of memory.
 * \param[in] priority The thread priority for the asyn port driver thread if
 *            ASYN_CANBLOCK is set in asynFlags.
 * \param[in] stackSize The stack size for the asyn port driver thread if
 *            ASYN_CANBLOCK is set in asynFlags.
 */
OdinDetector::OdinDetector(const char *portName, const char *serverHostname,
                           const char *detectorName, int maxBuffers,
                           size_t maxMemory, int priority, int stackSize)

    : ADDriver(portName, 2, 0, maxBuffers, maxMemory,
               asynEnumMask, asynEnumMask,    /* Add Enum interface */
               ASYN_CANBLOCK |                /* ASYN_CANBLOCK=1 */
                   ASYN_MULTIDEVICE,          /* ASYN_MULTIDEVICE=1 */
               1,                             /* autoConnect=1 */
               priority, stackSize),
    mAPI(detectorName, serverHostname, mProcessPluginName, 8080),
    mParams(this, &mAPI, pasynUserSelf) {

  strncpy(mHostname, serverHostname, sizeof(mHostname));

  // Write version to appropriate parameter
  setStringParam(NDDriverVersion, DRIVER_VERSION);

  mAPIVersion = createRESTParam(OdinRestAPIVersion, REST_P_STRING, SSRoot, "api");
  mFirstParam = mAPIVersion->getIndex();

  if (mOdinDataLibraryPath.empty()) {
    asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
              "OdinData library path not set; not configuring processes\n");
  }
  else {
    mAPI.configureSharedMemoryChannels(mIPAddress, mReadyPort, mReleasePort);
    mAPI.loadFileWriterPlugin(mOdinDataLibraryPath);
    createOdinDataParams();
    if (mProcessPluginName.empty() || mDetectorLibraryPath.empty()) {
      asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
                "Detector name and library path not set; not loading detector ProcessPlugin\n");
    }
    else {
      mAPI.loadProcessPlugin(mDetectorLibraryPath, mProcessPluginName);
      mAPI.connectToFrameReceiver(mProcessPluginName);
      mAPI.connectToProcessPlugin(mAPI.FILE_WRITER_PLUGIN);
      mAPI.connectDetector();
      createDetectorParams();
    }
  }

  mParams.fetchAll();
}

void OdinDetector::configureOdinData(const char * libraryPath, const char * ipAddress,
                                     int readyPort, int releasePort, int metaPort) {
  mOdinDataLibraryPath = std::string(libraryPath);
  mIPAddress = ipAddress;
  mReadyPort = readyPort;
  mReleasePort = releasePort;
  mMetaPort = metaPort;
}

void OdinDetector::configureDetector(const char * detectorName, const char * libraryPath) {
  mProcessPluginName = std::string(detectorName);
  mDetectorLibraryPath = std::string(libraryPath);
}

RestParam *OdinDetector::createRESTParam(std::string const & asynName, rest_param_type_t restType,
                                         sys_t subSystem, std::string const & name, int arrayIndex)
{
  RestParam *p = mParams.create(asynName, restType, mAPI.sysStr(subSystem), name, arrayIndex);
  return p;
}

int OdinDetector::createDetectorParams()
{
  mConnected  = createRESTParam(OdinConnected,
                                REST_P_BOOL,   SSDetectorStatus, "connected");
  mNumPending = createRESTParam(OdinNumPending,
                                REST_P_UINT,   SSDetectorStatus, "num_pending");

  createParam(OdinHDF5ImageHeight, asynParamInt32, &mImageHeight);
  createParam(OdinHDF5ImageWidth,  asynParamInt32, &mImageWidth);
  createParam(OdinHDF5ChunkDepth,  asynParamInt32, &mChunkDepth);
  createParam(OdinHDF5ChunkHeight, asynParamInt32, &mChunkHeight);
  createParam(OdinHDF5ChunkWidth,  asynParamInt32, &mChunkWidth);

  setIntegerParam(mImageHeight, 512);
  setIntegerParam(mImageWidth,  2048);
  setIntegerParam(mChunkDepth,  1);
  setIntegerParam(mChunkHeight, 512);
  setIntegerParam(mChunkWidth,  2048);

  return 0;
}

int OdinDetector::createOdinDataParams()
{
  mProcesses  = createRESTParam(OdinNumProcesses,
                                REST_P_INT,    SSDataStatusHDF, "processes", 0);
  mFilePath   = createRESTParam(NDFilePathString,
                                REST_P_STRING, SSDataStatusHDF, "file_path", 0);
  mFileName   = createRESTParam(NDFileNameString,
                                REST_P_STRING, SSDataStatusHDF, "file_name", 0);
  return 0;
}

asynStatus OdinDetector::getStatus()
{
  int status = 0;

  // Fetch status items
  status |= mConnected->fetch();
  status |= mNumPending->fetch();
  status |= mProcesses->fetch();
  status |= mFilePath->fetch();
  status |= mFileName->fetch();

  if(status) {
    return asynError;
  }

  callParamCallbacks();
  return asynSuccess;
}

asynStatus OdinDetector::acquireStart(const std::string &fileName, const std::string &filePath,
                                      const std::string &datasetName, int dataType)
{
  mAPI.createFile(fileName, filePath);
  std::vector<int> imageDims = getImageDimensions();
  std::vector<int> chunkDims = getChunkDimensions();
  mAPI.createDataset(datasetName, dataType, imageDims, chunkDims);
  mAPI.startWrite();
  mAPI.startAcquisition();
  return asynSuccess;
}

asynStatus OdinDetector::acquireStop()
{
  mAPI.stopAcquisition();
  mAPI.stopWrite();
  return asynSuccess;
}

std::vector<int> OdinDetector::getImageDimensions()
{
  std::vector<int> dims(2);
  getIntegerParam(mImageHeight, &dims[0]);
  getIntegerParam(mImageWidth, &dims[1]);
  asynPrint(pasynUserSelf, ASYN_TRACE_FLOW, "Image Dimensions: [%d, %d]\n", dims[0], dims[1]);

  return dims;
}

std::vector<int> OdinDetector::getChunkDimensions()
{
  std::vector<int> dims(3);
  getIntegerParam(mChunkDepth, &dims[0]);
  getIntegerParam(mChunkHeight, &dims[1]);
  getIntegerParam(mChunkWidth, &dims[2]);
  asynPrint(pasynUserSelf, ASYN_TRACE_FLOW,
            "Chunk Dimensions: [%d, %d, %d]\n", dims[0], dims[1], dims[2]);

  return dims;
}

/* Called when asyn clients call pasynInt32->write().
 * This function performs actions for some parameters, including ADAcquire, ADTriggerMode, etc.
 * For all parameters it sets the value in the parameter library and calls any registered callbacks.
 *
 * \param[in] pasynUser pasynUser structure that encodes the reason and address.
 * \param[in] value Value to write.
 */
asynStatus OdinDetector::writeInt32(asynUser *pasynUser, epicsInt32 value) {
  int function = pasynUser->reason;
  asynStatus status = asynSuccess;
  const char *functionName = "writeInt32";

  int adStatus;
  getIntegerParam(ADStatus, &adStatus);

  if(function == ADAcquire) {
    if(value && adStatus != ADStatusAcquire) {
      acquireStart("test_file", "/tmp", "data", 2);
      setIntegerParam(ADStatus, ADStatusAcquire);
      setStringParam(ADStatusMessage, "Acquisition started");
    }
    else if (!value && adStatus == ADStatusAcquire) {
      acquireStop();
      setIntegerParam(ADStatus, ADStatusAborted);
      setStringParam(ADStatusMessage, "Acquisition aborted");
    }
    setIntegerParam(ADAcquire, value);
  }
  callParamCallbacks();

  status = setIntegerParam(function, value);

  if (function == ADReadStatus) {
    status = getStatus();
  }
  else if(function < mFirstParam) {
    status = ADDriver::writeInt32(pasynUser, value);
  } else if (RestParam * p = mParams.getByIndex(function)){
    p->put(value);
  }

  if (status) {
    asynPrint(
        pasynUser, ASYN_TRACE_ERROR,
        "%s:%s error, status=%d function=%d, value=%d\n",
        driverName, functionName, status, function, value);
  }
  else {
    asynPrint(
        pasynUser, ASYN_TRACEIO_DRIVER, "%s:%s: function=%d, value=%d\n",
        driverName, functionName, function, value);

    callParamCallbacks();
  }

  return status;
}

/* Called when asyn clients call pasynFloat64->write().
 * This function performs actions for some parameters, including ADAcquireTime,
 * ADAcquirePeriod, etc.
 * For all parameters it sets the value in the parameter library and calls any
 * registered callbacks..
 * \param[in] pasynUser pasynUser structure that encodes the reason and
 *            address.
 * \param[in] value Value to write.
 */
asynStatus OdinDetector::writeFloat64(asynUser *pasynUser, epicsFloat64 value)
{
  int function = pasynUser->reason;
  asynStatus status = asynSuccess;
  const char *functionName = "writeFloat64";

  status = ADDriver::writeFloat64(pasynUser, value);

  if (status) {
    asynPrint(pasynUser, ASYN_TRACE_ERROR,
              "%s:%s error, status=%d function=%d, value=%f\n",
              driverName, functionName, status, function, value);
  } else {
    asynPrint(pasynUser, ASYN_TRACEIO_DRIVER,
              "%s:%s: function=%d, value=%f\n",
              driverName, functionName, function, value);

    callParamCallbacks();
  }

  return status;
}

/** Called when asyn clients call pasynOctet->write().
  * This function performs actions for EigerFWNamePattern
  * For all parameters it sets the value in the parameter library and calls any
  * registered callbacks.
  * \param[in] pasynUser pasynUser structure that encodes the reason and address.
  * \param[in] value Address of the string to write.
  * \param[in] nChars Number of characters to write.
  * \param[out] nActual Number of characters actually written. */
asynStatus OdinDetector::writeOctet(asynUser *pasynUser, const char *value,
                                    size_t nChars, size_t *nActual) {
  int function = pasynUser->reason;
  asynStatus status = asynSuccess;
  const char *functionName = "writeOctet";

  status = ADDriver::writeOctet(pasynUser, value, nChars, nActual);

  if (status) {
    asynPrint(pasynUser, ASYN_TRACE_ERROR,
              "%s:%s: status=%d, function=%d, value=%s",
              driverName, functionName, status, function, value);
  } else {
    asynPrint(pasynUser, ASYN_TRACEIO_DRIVER,
              "%s:%s: function=%d, value=%s\n",
              driverName, functionName, function, value);

    callParamCallbacks();
  }

  *nActual = nChars;
  return status;
}

/* Report status of the driver.
 * Prints details about the driver if details>0.
 * It then calls the ADDriver::report() method.
 * \param[in] fp File pointed passed by caller where the output is written to.
 * \param[in] details If >0 then driver details are printed.
 */
void OdinDetector::report(FILE *fp, int details) {
  // Invoke the base class method
  ADDriver::report(fp, details);
}

asynStatus OdinDetector::drvUserCreate(asynUser *pasynUser,
                                       const char *drvInfo,
                                       const char **pptypeName,
                                       size_t *psize)
{
  static const char *functionName = "drvUserCreate";
  asynStatus status = asynSuccess;
  int index;
  RestParam * generatedParam;
  std::string value;

  // Retrieve the name of the variable
  char * httpRequest = epicsStrDup(drvInfo + 4);

  std::stringstream temp;
  temp << httpRequest;
  std::string uri = temp.str();
  std::string name;
  name = uri.substr(uri.rfind("/" + 1));

  // Accepted parameter formats for HTTP parameters
  //
  // ODI_...  => Integer parameter
  // ODE_...  => Enum parameter
  // ODS_...  => String parameter
  // ODD_...  => Double parameter
  if (findParam(drvInfo, &index) && strlen(drvInfo) > 4 && strncmp(drvInfo, "OD", 2) == 0 &&
      drvInfo[3] == '_') {

    RestParam * existingParam = mParams.getByName(drvInfo);
    if (existingParam == NULL || existingParam->getName() != name) {
      // If param doesn't already exist -- Create it
      // If param does already exist and is bound the the same URI
      // -- Ignore - this is probably the *_RBV record
      // If param does already exist, but it is bound to a different URI
      // -- Let it try to create it and throw an exception, as it would if manually created

      asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                "%s:%s: Creating new parameter with URI: %s\n",
                driverName, functionName, httpRequest);
      // Check for I, D or S in drvInfo[2]
      switch (drvInfo[2]) {
      case 'I':
        // Create the parameter
        asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                  "%s:%s: Integer parameter: %s\n",
                  driverName, functionName, drvInfo);
        generatedParam = createRESTParam(drvInfo, REST_P_INT, SSDetector, httpRequest, 0);
        generatedParam->fetch();
        // Store the parameter
        break;
      case 'E':
        // Create the parameter
        asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                  "%s:%s: Enum parameter: %s\n",
                  driverName, functionName, drvInfo);
        generatedParam = createRESTParam(drvInfo, REST_P_ENUM, SSDetector, httpRequest, 0);
        generatedParam->fetch();
        // Store the parameter
        break;
        case 'D':
          // Create the parameter
          asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                    "%s:%s: Double parameter: %s\n",
                    driverName, functionName, drvInfo);
          generatedParam = createRESTParam(drvInfo, REST_P_DOUBLE, SSDetector, httpRequest, 0);
          generatedParam->fetch();
          // Store the parameter
          break;
        case 'S':
          // Create the parameter
          asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                    "%s:%s: String parameter: %s\n",
                    driverName, functionName, drvInfo);
          generatedParam = createRESTParam(drvInfo, REST_P_STRING, SSDetector, httpRequest, 0);
          generatedParam->fetch();
          // Store the parameter
          break;
        default:
          asynPrint(this->pasynUserSelf, ASYN_TRACE_ERROR,
                    "%s:%s: Expected ODx_... where x is one of I, D or S. Got '%c'\n",
                    driverName, functionName, drvInfo[2]);
          status = asynError;
      }
    }
  }

  if (status == asynSuccess) {
    // Now return baseclass result
    status = ADDriver::drvUserCreate(pasynUser, drvInfo, pptypeName, psize);
  }
  return status;
}

extern "C" int odinDetectorConfig(const char *portName,
                                  const char *serverPort,
                                  const char *detectorName,
                                  int maxBuffers,
                                  size_t maxMemory,
                                  int priority,
                                  int stackSize) {
  new OdinDetector(portName, serverPort, detectorName,
                   maxBuffers, maxMemory, priority,
                   stackSize);
  return asynSuccess;
}

extern "C" int odinDataConfig(const char * libraryPath, const char * ipAddress,
                              int readyPort, int releasePort, int metaPort) {
  OdinDetector::configureOdinData(libraryPath, ipAddress, readyPort, releasePort, metaPort);
  return asynSuccess;
}

extern "C" int odinDataDetectorConfig(const char * detectorName, const char * libraryPath) {
  OdinDetector::configureDetector(detectorName, libraryPath);
  return asynSuccess;
}

// Code for iocsh registration
static const iocshArg odinDetectorConfigArg0 = {"Port name", iocshArgString};
static const iocshArg odinDetectorConfigArg1 = {"Server host name",
                                                iocshArgString};
static const iocshArg odinDetectorConfigArg2 = {"Detector name", iocshArgString};
static const iocshArg odinDetectorConfigArg3 = {"maxBuffers", iocshArgInt};
static const iocshArg odinDetectorConfigArg4 = {"maxMemory", iocshArgInt};
static const iocshArg odinDetectorConfigArg5 = {"priority", iocshArgInt};
static const iocshArg odinDetectorConfigArg6 = {"stackSize", iocshArgInt};
static const iocshArg *const odinDetectorConfigArgs[] = {
    &odinDetectorConfigArg0, &odinDetectorConfigArg1,
    &odinDetectorConfigArg2, &odinDetectorConfigArg3,
    &odinDetectorConfigArg4, &odinDetectorConfigArg5,
    &odinDetectorConfigArg6};

static const iocshFuncDef configOdinDetector = {"odinDetectorConfig",
                                                7, odinDetectorConfigArgs};

static void configOdinDetectorCallFunc(const iocshArgBuf *args) {
  odinDetectorConfig(args[0].sval, args[1].sval, args[2].sval,
                     args[3].ival, args[4].ival, args[5].ival,
                     args[6].ival);
}

static void odinDetectorRegister() {
  iocshRegister(&configOdinDetector, configOdinDetectorCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDetectorRegister);
}

static const iocshArg odinDataConfigArg0 = {"Dynamic library path", iocshArgString};
static const iocshArg odinDataConfigArg1 = {"IP address of OdinData processes", iocshArgString};
static const iocshArg odinDataConfigArg2 = {"Ready port", iocshArgInt};
static const iocshArg odinDataConfigArg3 = {"Release port", iocshArgInt};
static const iocshArg odinDataConfigArg4 = {"Meta port", iocshArgInt};
static const iocshArg *const odinDataConfigArgs[] = {
    &odinDataConfigArg0, &odinDataConfigArg1,
    &odinDataConfigArg2, &odinDataConfigArg3, &odinDataConfigArg4};

static const iocshFuncDef configOdinData = {"odinDataConfig", 5, odinDataConfigArgs};

static void configOdinDataCallFunc(const iocshArgBuf *args) {
  odinDataConfig(args[0].sval, args[1].sval,
                 args[2].ival, args[3].ival, args[4].ival);
}

static void odinDataRegister() {
  iocshRegister(&configOdinData, configOdinDataCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataRegister);
}

static const iocshArg odinDataDetectorConfigArg0 = {"Detector name", iocshArgString};
static const iocshArg odinDataDetectorConfigArg1 = {"Dynamic library path", iocshArgString};
static const iocshArg *const odinDataDetectorConfigArgs[] = {
    &odinDataDetectorConfigArg0, &odinDataDetectorConfigArg1};

static const iocshFuncDef configOdinDataDetector = {"odinDataDetectorConfig", 2,
                                                    odinDataDetectorConfigArgs};

static void configOdinDataDetectorCallFunc(const iocshArgBuf *args) {
  odinDataDetectorConfig(args[0].sval, args[1].sval);
}

static void odinDataDetectorRegister() {
  iocshRegister(&configOdinDataDetector, configOdinDataDetectorCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataDetectorRegister);
}

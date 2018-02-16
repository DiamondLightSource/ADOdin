#include "odinDetector.h"

#include <sstream>
#include <numeric>

#include <epicsExport.h>
#include <epicsString.h>
#include <iocsh.h>
#include <drvSup.h>

static const std::string DRIVER_VERSION("0-1");
static const char *driverName = "OdinDetector";

// These parameters are optionally configured by ioc init commands
std::string                  OdinDetector::mOdinDataLibraryPath = "";
std::vector<ODConfiguration> OdinDetector::mODConfig                ;
size_t                       OdinDetector::mODCount             =  0;
std::string                  OdinDetector::mDatasetName         = "";
std::string                  OdinDetector::mProcessPluginName   = "";
std::string                  OdinDetector::mDetectorLibraryPath = "";

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
OdinDetector::OdinDetector(const char *portName, const char *serverHostname, int odinServerPort,
                           const char *detectorName, int maxBuffers,
                           size_t maxMemory, int priority, int stackSize)

    : ADDriver(portName, 2, 0, maxBuffers, maxMemory,
               asynEnumMask, asynEnumMask,    /* Add Enum interface */
               ASYN_CANBLOCK |                /* ASYN_CANBLOCK=1 */
                   ASYN_MULTIDEVICE,          /* ASYN_MULTIDEVICE=1 */
               1,                             /* autoConnect=1 */
               priority, stackSize),
    mAPI(detectorName, serverHostname, mProcessPluginName, odinServerPort),
    mParams(this, &mAPI, pasynUserSelf) {

  strncpy(mHostname, serverHostname, sizeof(mHostname));

  // Write version to appropriate parameter
  setStringParam(NDDriverVersion, DRIVER_VERSION);

  mAPIVersion = createODRESTParam(OdinRestAPIVersion, REST_P_STRING, SSRoot, "api");
  mFirstParam = mAPIVersion->getIndex();

  if (initialiseAll()) {
    asynPrint(pasynUserSelf, ASYN_TRACE_ERROR, "Failed to initialise all OdinData processes\n");
  }

  if (std::accumulate(mInitialised.begin(), mInitialised.end(), 0) > 0) {
    createOdinDataParams();
  }
  createDetectorParams();
  mParams.fetchAll();
}

int OdinDetector::initialiseAll()
{
  int status = 0;
  mInitialised.resize(mODCount);
  for (int index = 0; index != (int) mODConfig.size(); ++index) {
    status |= initialise(index);
  }
  return status;
}

int OdinDetector::initialise(int index)
{
  int status = 0;
  mInitialised[index] = 0;

  if (mOdinDataLibraryPath.empty()) {
    asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
              "OdinData library path not set; not configuring processes\n");
  }
  else {
    status |= mAPI.configureSharedMemoryChannels(mODConfig[index]);
    status |= mAPI.loadFileWriterPlugin(mOdinDataLibraryPath);
    status |= mAPI.createDataset(mDatasetName);
    if (mProcessPluginName.empty() || mDetectorLibraryPath.empty()) {
      asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
                "Detector name and library path not set; not loading detector ProcessPlugin\n");
    }
    else {
      status |= mAPI.loadProcessPlugin(mDetectorLibraryPath, mProcessPluginName);
      status |= mAPI.connectToFrameReceiver(mProcessPluginName);
      status |= mAPI.connectToProcessPlugin(mAPI.FILE_WRITER_PLUGIN);
      mAPI.connectDetector(); // Don't return failure if detector not available
    }
  }

  if (status) {
    asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
              "Failed to initialise OdinData process rank %d\n", index);
  }
  else {
    mInitialised[index] = 1;
  }
  return status;
}

void OdinDetector::configureOdinDataProcess(const char * ipAddress, int readyPort, int releasePort,
                                            int metaPort) {
  mODConfig.push_back(ODConfiguration(mODCount, ipAddress, readyPort, releasePort, metaPort));
  mODCount++;
}

void OdinDetector::configureOdinData(const char * odinDataLibraryPath,
                                     const char * detectorName, const char * detectorLibraryPath,
                                     const char * datasetName) {
  mOdinDataLibraryPath = std::string(odinDataLibraryPath);
  mProcessPluginName = std::string(detectorName);
  mDetectorLibraryPath = std::string(detectorLibraryPath);
  mDatasetName = std::string(datasetName);
}

RestParam * OdinDetector::createODRESTParam(const std::string& asynName, rest_param_type_t restType,
                                            sys_t subSystem, const std::string& name)
{
  RestParam * p = mParams.create(asynName, restType, mAPI.sysStr(subSystem), name, mODCount);
  return p;
}

RestParam * OdinDetector::createRESTParam(const std::string& asynName, rest_param_type_t restType,
                                          sys_t subSystem, const std::string& name,
                                          size_t arraySize)
{
  RestParam * p = mParams.create(asynName, restType, mAPI.sysStr(subSystem), name, arraySize);
  return p;
}

int OdinDetector::createDetectorParams()
{
  mConnected = createRESTParam(OdinDetectorConnected, REST_P_BOOL,
                               SSDetectorStatus, "connected");
  mNumImages = createRESTParam(ADNumImagesString, REST_P_INT,
                               SSDetectorConfig, "num_images");

  return 0;
}

int OdinDetector::createOdinDataParams()
{
  mProcesses              = createODRESTParam(OdinNumProcesses, REST_P_INT,
                                              SSDataConfigHDFProcess, "number");
  mFilePath               = createODRESTParam(NDFilePathString, REST_P_STRING,
                                              SSDataConfigHDF, "file/path");
  mFileName               = createODRESTParam(NDFileNameString, REST_P_STRING,
                                              SSDataConfigHDF, "file/name");
  mBlockSize              = createODRESTParam(OdinHDF5BlockSize, REST_P_INT,
                                              SSDataConfigHDFProcess, "frames_per_block");
  mBlocksPerFile          = createODRESTParam(OdinHDF5BlocksPerFile, REST_P_INT,
                                              SSDataConfigHDFProcess, "blocks_per_file");
  mEarliestVersion        = createODRESTParam(OdinHDF5EarliestVersion, REST_P_BOOL,
                                              SSDataConfigHDFProcess, "earliest_version");
  mMasterDataset          = createODRESTParam(OdinHDF5MasterDataset, REST_P_STRING,
                                              SSDataConfigHDF, "master");
  mOffsetAdjustment       = createODRESTParam(OdinHDF5OffsetAdjustment, REST_P_INT,
                                              SSDataConfigHDF, "offset");
  mAcquisitionID          = createODRESTParam(OdinHDF5AcquisitionID, REST_P_STRING,
                                              SSDataConfigHDF, "acquisition_id");
  mCloseFileTimeout       = createODRESTParam(OdinHDF5CloseFileTimeout, REST_P_INT,
                                              SSDataConfigHDF, "timeout_timer_period");
  mStartCloseTimeout      = createODRESTParam(OdinHDF5StartCloseTimeout, REST_P_BOOL,
                                              SSDataConfigHDF, "start_timeout_timer");
  mNumCapture             = createODRESTParam(OdinHDF5NumCapture, REST_P_INT,
                                              SSDataConfigHDF, "frames");
  mCapture                = createODRESTParam(OdinHDF5Write, REST_P_BOOL,
                                              SSDataConfigHDF, "write");
  mChunkBoundaryAlignment = createODRESTParam(OdinHDF5ChunkBoundaryAlignment, REST_P_INT,
                                              SSDataConfigHDF, "alignment_value");
  mChunkBoundaryThreshold = createODRESTParam(OdinHDF5ChunkBoundaryThreshold, REST_P_INT,
                                              SSDataConfigHDF, "alignment_threshold");
  mDataType               = createODRESTParam(OdinHDF5Compression, REST_P_INT,
                                              SSDataConfigHDFDataset, mDatasetName + "/compression");
  mCompression            = createODRESTParam(NDDataTypeString, REST_P_INT,
                                              SSDataConfigHDFDataset, mDatasetName + "/datatype");

  mProcessConnected       = createODRESTParam(OdinProcessConnected, REST_P_BOOL,
                                              SSDataStatus, "connected");
  mProcessRank            = createODRESTParam(OdinProcessRank, REST_P_INT,
                                              SSDataConfigHDFProcess, "rank");
  mWriting                = createODRESTParam(OdinHDF5Writing, REST_P_BOOL,
                                              SSDataStatusHDF, "writing");
  mFullFileName           = createODRESTParam(OdinHDF5FullFileName, REST_P_STRING,
                                              SSDataStatusHDF, "file_name");
  mNumCaptured            = createODRESTParam(OdinHDF5NumCaptured, REST_P_INT,
                                              SSDataStatusHDF, "frames_written");
  mNumExpected            = createODRESTParam(OdinHDF5NumExpected, REST_P_INT,
                                              SSDataStatusHDF, "frames_max");

  createParam(OdinProcessInitialised, asynParamInt32, &mProcessInitialised);
  createParam(OdinHDF5NumCapturedSum, asynParamInt32, &mNumCapturedSum);
  createParam(OdinHDF5WritingAny,     asynParamInt32, &mWritingAny);
  createParam(OdinHDF5FileTemplate,   asynParamOctet, &mFileTemplate);
  createParam(OdinHDF5ImageHeight,    asynParamInt32, &mImageHeight);
  createParam(OdinHDF5ImageWidth,     asynParamInt32, &mImageWidth);
  createParam(OdinHDF5ChunkDepth,     asynParamInt32, &mChunkDepth);
  createParam(OdinHDF5ChunkHeight,    asynParamInt32, &mChunkHeight);
  createParam(OdinHDF5ChunkWidth,     asynParamInt32, &mChunkWidth);

  setIntegerParam(mImageHeight, 512);
  setIntegerParam(mImageWidth,  2048);
  setIntegerParam(mChunkDepth,  1);
  setIntegerParam(mChunkHeight, 512);
  setIntegerParam(mChunkWidth,  2048);

  mOdinDataParamsCreated = true;
  return 0;
}

asynStatus OdinDetector::getStatus()
{
  int status = 0;

  // Fetch status items
  status |= mProcesses->fetch();
  status |= mFilePath->fetch();
  status |= mFileName->fetch();

  status |= mProcessConnected->fetch();
  status |= mProcessRank->fetch();
  status |= mWriting->fetch();
  status |= mFullFileName->fetch();
  status |= mNumCaptured->fetch();
  status |= mNumExpected->fetch();

  std::vector<int> numCaptured(mODCount);
  mNumCaptured->get(numCaptured);
  setIntegerParam(mNumCapturedSum, std::accumulate(numCaptured.begin(), numCaptured.end(), 0));

  std::vector<bool> writing(mODCount);
  mWriting->get(writing);
  setIntegerParam(mWritingAny, std::accumulate(writing.begin(), writing.end(), 0) == 0 ? 0 : 1);

  bool connected;
  for (int index = 0; index != (int) mODConfig.size(); ++index) {
    mProcessConnected->get(connected, index);
    if (!connected && mInitialised[index] == 1) {
      // Lost connection - Set not initialised
      mInitialised[index] = 0;
    }
    else if (mInitialised[index] == 0 && connected) {
      // Restored connection - Re-initialise
      initialise(index);
    }
    setIntegerParam(mProcessInitialised, mInitialised[index]);
  }

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

int OdinDetector::configureImageDims()
{
  int status = 0;
  std::vector<int> imageDims(2);
  status |= (int) getIntegerParam(mImageHeight, &imageDims[0]);
  status |= (int) getIntegerParam(mImageWidth, &imageDims[1]);
  asynPrint(pasynUserSelf, ASYN_TRACE_FLOW,
            "Image Dimensions: [%d, %d]\n", imageDims[0], imageDims[1]);

  status |= mAPI.setImageDims(mDatasetName, imageDims);
  return status;
}

int OdinDetector::configureChunkDims()
{
  int status = 0;
  std::vector<int> chunkDims(3);
  status |= (int) getIntegerParam(mChunkDepth, &chunkDims[0]);
  status |= (int) getIntegerParam(mChunkHeight, &chunkDims[1]);
  status |= (int) getIntegerParam(mChunkWidth, &chunkDims[2]);
  asynPrint(pasynUserSelf, ASYN_TRACE_FLOW,
            "Chunk Dimensions: [%d, %d, %d]\n", chunkDims[0], chunkDims[1], chunkDims[2]);

  status |= mAPI.setChunkDims(mDatasetName, chunkDims);
  return status;
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
  else if (function == mImageHeight || function == mImageWidth) {
    configureImageDims();
  }
  else if (function == mChunkDepth || function == mChunkHeight || function == mChunkWidth) {
    configureChunkDims();
  }
  else if (RestParam * p = mParams.getByIndex(function)) {
    p->put(value);
  }

  if(function < mFirstParam) {
    status = ADDriver::writeInt32(pasynUser, value);
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
  int status = 0;
  const char *functionName = "writeFloat64";

  if (RestParam * p = mParams.getByIndex(function)) {
    status |= p->put(value);
  }

  status |= ADDriver::writeFloat64(pasynUser, value);

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

  return (asynStatus) status;
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
  int status = 0;
  const char *functionName = "writeOctet";

  if (mOdinDataParamsCreated) {
    if (function == mFileTemplate || function == mAcquisitionID->getIndex()) {
      std::string acquisitionID, fileTemplate;
      mAcquisitionID->get(acquisitionID);
      getStringParam(mFileTemplate, fileTemplate);

      char buffer[fileTemplate.size() + acquisitionID.size() + 5];
      snprintf(buffer, sizeof(buffer), fileTemplate.c_str(), acquisitionID.c_str(), 1);
      mFileName->put(buffer);
    }
  }

  if (RestParam * p = mParams.getByIndex(function)) {
    status |= p->put(value);
  }

  status |= ADDriver::writeOctet(pasynUser, value, nChars, nActual);

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
  return (asynStatus) status;
}

asynStatus OdinDetector::callParamCallbacks()
{
  int status = 0;
  status |= (int) ADDriver::callParamCallbacks(0);
  status |= (int) ADDriver::callParamCallbacks(1);
  return (asynStatus) status;
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

extern "C" int odinDetectorConfig(const char *portName, const char *serverPort, int odinServerPort,
                                  const char *detectorName,
                                  int maxBuffers, size_t maxMemory, int priority, int stackSize) {
  new OdinDetector(portName, serverPort, odinServerPort, detectorName,
                   maxBuffers, maxMemory, priority, stackSize);
  return asynSuccess;
}

extern "C" int odinDataProcessConfig(const char * ipAddress, int readyPort, int releasePort,
                                     int metaPort) {
  OdinDetector::configureOdinDataProcess(ipAddress, readyPort, releasePort, metaPort);
  return asynSuccess;
}

extern "C" int odinDataConfig(const char * odinDataLibraryPath,
                              const char * detectorName, const char * libraryPath,
                              const char * datasetName) {
  OdinDetector::configureOdinData(odinDataLibraryPath, detectorName, libraryPath, datasetName);
  return asynSuccess;
}

// Code for iocsh registration
static const iocshArg odinDetectorConfigArg0 = {"Port name", iocshArgString};
static const iocshArg odinDetectorConfigArg1 = {"Server host name", iocshArgString};
static const iocshArg odinDetectorConfigArg2 = {"Odin server port", iocshArgInt};
static const iocshArg odinDetectorConfigArg3 = {"Detector name", iocshArgString};
static const iocshArg odinDetectorConfigArg4 = {"maxBuffers", iocshArgInt};
static const iocshArg odinDetectorConfigArg5 = {"maxMemory", iocshArgInt};
static const iocshArg odinDetectorConfigArg6 = {"priority", iocshArgInt};
static const iocshArg odinDetectorConfigArg7 = {"stackSize", iocshArgInt};
static const iocshArg *const odinDetectorConfigArgs[] = {
    &odinDetectorConfigArg0, &odinDetectorConfigArg1,
    &odinDetectorConfigArg2, &odinDetectorConfigArg3,
    &odinDetectorConfigArg4, &odinDetectorConfigArg5,
    &odinDetectorConfigArg6, &odinDetectorConfigArg7};

static const iocshFuncDef configOdinDetector = {"odinDetectorConfig", 8, odinDetectorConfigArgs};

static void configOdinDetectorCallFunc(const iocshArgBuf *args) {
  odinDetectorConfig(args[0].sval, args[1].sval, args[2].ival,
                     args[3].sval, args[4].ival, args[5].ival,
                     args[6].ival, args[7].ival);
}

static void odinDetectorRegister() {
  iocshRegister(&configOdinDetector, configOdinDetectorCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDetectorRegister);
}

static const iocshArg odinDataConfigArg0 = {"OdinData dynamic library path", iocshArgString};
static const iocshArg odinDataConfigArg1 = {"Detector name", iocshArgString};
static const iocshArg odinDataConfigArg2 = {"Detector library path", iocshArgString};
static const iocshArg odinDataConfigArg3 = {"Name of dataset", iocshArgString};
static const iocshArg *const odinDataConfigArgs[] = {
    &odinDataConfigArg0, &odinDataConfigArg1, &odinDataConfigArg2, &odinDataConfigArg3};

static const iocshFuncDef configOdinData = {"odinDataConfig", 4, odinDataConfigArgs};

static void configOdinDataCallFunc(const iocshArgBuf *args) {
  odinDataConfig(args[0].sval, args[1].sval, args[2].sval, args[3].sval);
}

static void odinDataRegister() {
  iocshRegister(&configOdinData, configOdinDataCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataRegister);
}

static const iocshArg odinDataProcessConfigArg0 = {"IP address", iocshArgString};
static const iocshArg odinDataProcessConfigArg1 = {"Ready port", iocshArgInt};
static const iocshArg odinDataProcessConfigArg2 = {"Release port", iocshArgInt};
static const iocshArg odinDataProcessConfigArg3 = {"Meta port", iocshArgInt};
static const iocshArg *const odinDataProcessConfigArgs[] = {
    &odinDataProcessConfigArg0, &odinDataProcessConfigArg1, &odinDataProcessConfigArg2,
    &odinDataProcessConfigArg3};

static const iocshFuncDef configOdinDataProcess = {
    "odinDataProcessConfig", 4, odinDataProcessConfigArgs};

static void configOdinDataProcessCallFunc(const iocshArgBuf *args) {
  odinDataProcessConfig(args[0].sval, args[1].ival, args[2].ival, args[3].ival);
}

static void odinDataProcessRegister() {
  iocshRegister(&configOdinDataProcess, configOdinDataProcessCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataProcessRegister);
}

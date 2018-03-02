#include "odinDataDriver.h"

#include <sstream>
#include <numeric>
#include <algorithm>

#include <epicsExport.h>
#include <epicsString.h>
#include <iocsh.h>
#include <drvSup.h>

static const char *driverName = "OdinDataDriver";

// These parameters are optionally configured by ioc init commands
std::string                  OdinDataDriver::mFileWriterLibraryPath    = "";
std::vector<ODConfiguration> OdinDataDriver::mODConfig                     ;
size_t                       OdinDataDriver::mODCount                  =  0;
std::string                  OdinDataDriver::mDatasetName              = "";
std::string                  OdinDataDriver::mProcessPluginName        = "";
std::string                  OdinDataDriver::mProcessPluginLibraryPath = "";

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
OdinDataDriver::OdinDataDriver(const char * portName, const char * serverHostname,
                               int odinServerPort,
                               const char * datasetName, const char * fileWriterLibraryPath,
                               const char * detectorName, const char * processPluginLibraryPath,
                               int maxBuffers, size_t maxMemory, int priority, int stackSize)

    : OdinClient(portName, serverHostname, odinServerPort,
                 detectorName, maxBuffers,
                 maxMemory, priority, stackSize),
    mAPI(serverHostname, mProcessPluginName, odinServerPort)
{
  mDatasetName = std::string(datasetName);
  mFileWriterLibraryPath = std::string(fileWriterLibraryPath);
  mProcessPluginName = std::string(detectorName);
  mProcessPluginLibraryPath = std::string(processPluginLibraryPath);

  strncpy(mHostname, serverHostname, sizeof(mHostname));

  // Register the detector API with the Odin client parent
  this->registerAPI(&mAPI);

  if (initialiseAll()) {
    asynPrint(pasynUserSelf, ASYN_TRACE_ERROR, "Failed to initialise all OdinData processes\n");
  }

  if (std::accumulate(mInitialised.begin(), mInitialised.end(), 0) > 0) {
    createOdinDataParams();
  }
//  createDetectorParams();
  this->fetchParams();
}

int OdinDataDriver::initialiseAll()
{
  int status = 0;
  mInitialised.resize(mODCount);
  for (int index = 0; index != (int) mODConfig.size(); ++index) {
    status |= initialise(index);
  }
  return status;
}

int OdinDataDriver::initialise(int index)
{
  int status = 0;
  mInitialised[index] = 0;

  if (mFileWriterLibraryPath.empty()) {
    asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
              "OdinData library path not set; not configuring processes\n");
  }
  else {
    status |= mAPI.configureSharedMemoryChannels(mODConfig[index]);
    status |= mAPI.loadFileWriterPlugin(mFileWriterLibraryPath);
    status |= mAPI.createDataset(mDatasetName);
    if (mProcessPluginName.empty() || mProcessPluginLibraryPath.empty()) {
      asynPrint(pasynUserSelf, ASYN_TRACE_WARNING,
                "Detector name and library path not set; not loading detector ProcessPlugin\n");
    }
    else {
      status |= mAPI.loadProcessPlugin(mProcessPluginLibraryPath, mProcessPluginName);
      status |= mAPI.connectToFrameReceiver(mProcessPluginName);
      status |= mAPI.connectToProcessPlugin(mAPI.FILE_WRITER_PLUGIN);
    }
  }

  if (status) {
    asynPrint(pasynUserSelf, ASYN_TRACE_ERROR,
              "Failed to initialise OdinData process rank %d\n", index);
  }
  else {
    mInitialised[index] = 1;
  }
  return status;
}

void OdinDataDriver::configureOdinDataProcess(const char * ipAddress, int readyPort, int releasePort,
                                            int metaPort) {
  mODConfig.push_back(ODConfiguration(mODCount, ipAddress, readyPort, releasePort, metaPort));
  mODCount++;
}

int OdinDataDriver::createOdinDataParams()
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
                                              SSDataConfigHDFProcess, "alignment_value");
  mChunkBoundaryThreshold = createODRESTParam(OdinHDF5ChunkBoundaryThreshold, REST_P_INT,
                                              SSDataConfigHDFProcess, "alignment_threshold");
  mDataType               = createODRESTParam(OdinHDF5Compression, REST_P_INT,
                                              SSDataConfigHDFDataset, mDatasetName + "/datatype");
  mCompression            = createODRESTParam(NDDataTypeString, REST_P_INT,
                                              SSDataConfigHDFDataset, mDatasetName + "/compression");


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

  mCapture->setCommand();
  mStartCloseTimeout->setCommand();

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

RestParam * OdinDataDriver::createODRESTParam(const std::string& asynName,
                                              rest_param_type_t restType,
                                              sys_t subSystem, const std::string& name)
{
  return createRESTParam(asynName, restType, subSystem, name, mODCount);
}

asynStatus OdinDataDriver::getStatus()
{
  int status = 0;

  // Fetch status items
  status = this->fetchParams();

  if (!mAPI.connected()){
    setIntegerParam(ADStatus, ADStatusDisconnected);
    setStringParam(ADStatusMessage, "Unable to connect to Odin Server");
  } else {
    int status = 0;
    getIntegerParam(ADStatus, &status);
    if (status == ADStatusDisconnected){
      setIntegerParam(ADStatus, ADStatusIdle);
    }
    // Check for any errors
    // If we are connected to the server then all errors are generated by
    // the server itself.
    std::string error_msg = "";
    mErrorMessage->get(error_msg);
    setStringParam(ADStatusMessage, error_msg.c_str());
    if (error_msg != ""){
      setIntegerParam(ADStatus, ADStatusError);
    }
  }

  if (mOdinDataParamsCreated) {
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
  }

  if(status) {
    return asynError;
  }

  callParamCallbacks();
  return asynSuccess;
}

asynStatus OdinDataDriver::acquireStart(const std::string &fileName, const std::string &filePath,
                                      const std::string &datasetName, int dataType)
{
  mAPI.createFile(fileName, filePath);
  mAPI.startWrite();
  return asynSuccess;
}

asynStatus OdinDataDriver::acquireStop()
{
  mAPI.stopWrite();
  return asynSuccess;
}

int OdinDataDriver::configureImageDims()
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

int OdinDataDriver::configureChunkDims()
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
asynStatus OdinDataDriver::writeInt32(asynUser *pasynUser, epicsInt32 value) {
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
  else if (RestParam * p = this->getParamByIndex(function)) {
    if (function == mCapture->getIndex() || function == mStartCloseTimeout->getIndex()) {
      p->put((bool) value);
    }
    else {
      p->put(value);
    }
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
asynStatus OdinDataDriver::writeFloat64(asynUser *pasynUser, epicsFloat64 value)
{
  int function = pasynUser->reason;
  int status = 0;
  const char *functionName = "writeFloat64";

  if (RestParam * p = this->getParamByIndex(function)) {
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
asynStatus OdinDataDriver::writeOctet(asynUser *pasynUser, const char *value,
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

  if (RestParam * p = this->getParamByIndex(function)) {
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

asynStatus OdinDataDriver::callParamCallbacks()
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
void OdinDataDriver::report(FILE *fp, int details) {
  // Invoke the base class method
  ADDriver::report(fp, details);
}

asynStatus OdinDataDriver::drvUserCreate(asynUser *pasynUser,
                                       const char *drvInfo,
                                       const char **pptypeName,
                                       size_t *psize)
{
  asynStatus status = asynSuccess;

  status = this->dynamicParam(pasynUser, drvInfo, pptypeName, psize, SSDataConfig);

  if (status == asynSuccess) {
    // Now return baseclass result
    status = ADDriver::drvUserCreate(pasynUser, drvInfo, pptypeName, psize);
  }
  return status;
}

extern "C" int odinDataDriverConfig(const char * portName, const char * serverPort,
                                    int odinServerPort,
                                    const char * datasetName, const char * fileWriterLibraryPath,
                                    const char * detectorName, const char * processPluginLibraryPath,
                                    int maxBuffers, size_t maxMemory, int priority, int stackSize) {
  new OdinDataDriver(portName, serverPort, odinServerPort,
                     datasetName, fileWriterLibraryPath,
                     detectorName, processPluginLibraryPath,
                     maxBuffers, maxMemory, priority, stackSize);
  return asynSuccess;
}

extern "C" int odinDataProcessConfig(const char * ipAddress, int readyPort, int releasePort,
                                     int metaPort) {
  OdinDataDriver::configureOdinDataProcess(ipAddress, readyPort, releasePort, metaPort);
  return asynSuccess;
}

// Code for iocsh registration
static const iocshArg odinDataDriverConfigArg0 = {"Port name", iocshArgString};
static const iocshArg odinDataDriverConfigArg1 = {"Server host name", iocshArgString};
static const iocshArg odinDataDriverConfigArg2 = {"Odin server port", iocshArgInt};
static const iocshArg odinDataDriverConfigArg3 = {"Name of dataset", iocshArgString};
static const iocshArg odinDataDriverConfigArg4 = {"FileWriter dynamic library path", iocshArgString};
static const iocshArg odinDataDriverConfigArg5 = {"Detector name", iocshArgString};
static const iocshArg odinDataDriverConfigArg6 = {"ProcessPlugin library path", iocshArgString};
static const iocshArg odinDataDriverConfigArg7 = {"maxBuffers", iocshArgInt};
static const iocshArg odinDataDriverConfigArg8 = {"maxMemory", iocshArgInt};
static const iocshArg odinDataDriverConfigArg9 = {"priority", iocshArgInt};
static const iocshArg odinDataDriverConfigArg10 = {"stackSize", iocshArgInt};
static const iocshArg *const odinDataDriverConfigArgs[] = {
    &odinDataDriverConfigArg0, &odinDataDriverConfigArg1,
    &odinDataDriverConfigArg2, &odinDataDriverConfigArg3,
    &odinDataDriverConfigArg4, &odinDataDriverConfigArg5,
    &odinDataDriverConfigArg6, &odinDataDriverConfigArg7,
    &odinDataDriverConfigArg8, &odinDataDriverConfigArg9, &odinDataDriverConfigArg10};

static const iocshFuncDef configOdinDataDriver = {"odinDataDriverConfig",
                                                  10, odinDataDriverConfigArgs};

static void configOdinDataDriverCallFunc(const iocshArgBuf *args) {
  odinDataDriverConfig(args[0].sval, args[1].sval, args[2].ival,
                       args[3].sval, args[4].sval, args[5].sval,
                       args[6].sval, args[7].ival, args[8].ival,
                       args[9].ival, args[10].ival);
}

static void odinDataDriverRegister() {
  iocshRegister(&configOdinDataDriver, configOdinDataDriverCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataDriverRegister);
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

#include "OdinDataDriver.h"

#include <sstream>
#include <numeric>
#include <algorithm>

#include <epicsExport.h>
#include <iocsh.h>

static const char *driverName = "OdinDataDriver";

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
OdinDataDriver::OdinDataDriver(const char* portName, const char* serverHostname,
                               int odinServerPort, int odinDataCount,
                               const char* datasetName, const char* detectorName,
                               int maxBuffers, size_t maxMemory, int priority, int stackSize)

    : OdinClient(portName, serverHostname, odinServerPort,
                 detectorName, maxBuffers,
                 maxMemory, priority, stackSize),
    mAPI(serverHostname, detectorName, odinServerPort, odinDataCount)
{
  mDatasetName = std::string(datasetName);
  mODCount = odinDataCount;

  strncpy(mHostname, serverHostname, sizeof(mHostname));

  // Register the detector API with the Odin client parent
  this->registerAPI(&mAPI);

  createParams();
  fetchParams();
}

int OdinDataDriver::createParams()
{
  mAPIVersion = createRESTParam(OdinRestAPIVersion, REST_P_STRING, SSRoot, "api");
  // Create a parameter to store any error message from the Odin server
  mErrorMessage = createRESTParam("ERR_MESSAGE", REST_P_STRING, SSFP, "status/error");
  mFirstParam = mAPIVersion->getIndex();

  // OdinServer Parameters
  mFPCount                = createRESTParam(OdinFPCount, REST_P_INT,
                                            SSFP, "count");
  mFRCount                = createRESTParam(OdinFRCount, REST_P_INT,
                                            SSFR, "count");
  // Configuration parameters shared by each OD process
  mFileExtension          = createODRESTParam(OdinHDF5FileExtension, REST_P_STRING,
                                              SSFPConfigHDF, "file/extension");
  mBlockSize              = createODRESTParam(OdinHDF5BlockSize, REST_P_INT,
                                              SSFPConfigHDFProcess, "frames_per_block");
  mBlocksPerFile          = createODRESTParam(OdinHDF5BlocksPerFile, REST_P_INT,
                                              SSFPConfigHDFProcess, "blocks_per_file");
  mEarliestVersion        = createODRESTParam(OdinHDF5EarliestVersion, REST_P_BOOL,
                                              SSFPConfigHDFProcess, "earliest_version");
  mMasterDataset          = createODRESTParam(OdinHDF5MasterDataset, REST_P_STRING,
                                              SSFPConfigHDF, "master");
  mCloseFileTimeout       = createODRESTParam(OdinHDF5CloseFileTimeout, REST_P_INT,
                                              SSFPConfigHDF, "timeout_timer_period");
  mChunkBoundaryAlignment = createODRESTParam(OdinHDF5ChunkBoundaryAlignment, REST_P_INT,
                                              SSFPConfigHDFProcess, "alignment_value");
  mChunkBoundaryThreshold = createODRESTParam(OdinHDF5ChunkBoundaryThreshold, REST_P_INT,
                                              SSFPConfigHDFProcess, "alignment_threshold");
  mDataType               = createODRESTParam(NDDataTypeString, REST_P_ENUM,
                                              SSFPConfigHDFDataset, mDatasetName + "/datatype");
  mCompression            = createODRESTParam(OdinHDF5Compression, REST_P_ENUM,
                                              SSFPConfigHDFDataset, mDatasetName + "/compression");
  // Parameters fanned out to all processes - not array based
  mStartCloseTimeout      = createRESTParam(OdinHDF5StartCloseTimeout, REST_P_BOOL,
                                            SSFPConfigHDF, "start_timeout_timer");
  mNumCapture             = createRESTParam(OdinHDF5NumCapture, REST_P_INT,
                                            SSFPConfigHDF, "frames");
  mCapture                = createRESTParam(OdinHDF5Write, REST_P_BOOL,
                                            SSFPConfigHDF, "write");
  // Per OD Process Status Parameters
  mFRProcessConnected     = createODRESTParam(OdinFRProcessConnected, REST_P_BOOL,
                                              SSFRStatus, "connected");
  mFPProcessConnected     = createODRESTParam(OdinFPProcessConnected, REST_P_BOOL,
                                              SSFPStatus, "connected");
  mProcessRank            = createODRESTParam(OdinProcessRank, REST_P_INT,
                                              SSFPStatusHDF, "rank");
  mWriting                = createODRESTParam(OdinHDF5Writing, REST_P_BOOL,
                                              SSFPStatusHDF, "writing");
  mTimeoutActive          = createODRESTParam(OdinHDF5TimeoutActive, REST_P_BOOL,
                                              SSFPStatusHDF, "timeout_active");
  mFullFileName           = createODRESTParam(OdinHDF5FullFileName, REST_P_STRING,
                                              SSFPStatusHDF, "file_name");
  mNumCaptured            = createODRESTParam(OdinHDF5NumCaptured, REST_P_INT,
                                              SSFPStatusHDF, "frames_processed");
  mNumExpected            = createODRESTParam(OdinHDF5NumExpected, REST_P_INT,
                                              SSFPStatusHDF, "frames_max");
  mFreeBuffers            = createODRESTParam(OdinFRFreeBuffers, REST_P_INT,
                                              SSFRStatus, "buffers/empty");
  mFramesReceived         = createODRESTParam(OdinFRFramesReceived, REST_P_INT,
                                              SSFRStatus, "frames/received");
  mFramesDropped          = createODRESTParam(OdinFRFramesDropped, REST_P_INT,
                                              SSFRStatus, "frames/dropped");
  mFramesTimedOut         = createODRESTParam(OdinFRFramesTimedOut, REST_P_INT,
                                              SSFRStatus, "frames/timedout");
  mFramesReleased         = createODRESTParam(OdinFRFramesReleased, REST_P_INT,
                                              SSFRStatus, "frames/released");

  mCapture->setCommand();
  mStartCloseTimeout->setCommand();

  // Set enum values
  std::vector<std::string> dataTypeEnum;
  dataTypeEnum.push_back("unknown");
  dataTypeEnum.push_back("uint8");
  dataTypeEnum.push_back("uint16");
  dataTypeEnum.push_back("uint32");
  dataTypeEnum.push_back("uint64");
  dataTypeEnum.push_back("float");
  mDataType->setEnumValues(dataTypeEnum);
  std::vector<std::string> compressionEnum;
  compressionEnum.push_back("unknown");
  compressionEnum.push_back("none");
  compressionEnum.push_back("LZ4");
  compressionEnum.push_back("BSLZ4");
  compressionEnum.push_back("blosc");
  mCompression->setEnumValues(compressionEnum);

  // Internal parameters
  createParam(OdinFPErrorState,         asynParamInt32, &mFPErrorState);
  createParam(OdinHDF5NumCapturedSum,   asynParamInt32, &mNumCapturedSum);
  createParam(OdinHDF5WritingAny,       asynParamInt32, &mWritingAny);
  createParam(OdinHDF5TimeoutActiveAny, asynParamInt32, &mTimeoutActiveAny);
  createParam(OdinHDF5ImageHeight,      asynParamInt32, &mImageHeight);
  createParam(OdinHDF5ImageWidth,       asynParamInt32, &mImageWidth);
  createParam(OdinHDF5ChunkDepth,       asynParamInt32, &mChunkDepth);
  createParam(OdinHDF5ChunkHeight,      asynParamInt32, &mChunkHeight);
  createParam(OdinHDF5ChunkWidth,       asynParamInt32, &mChunkWidth);
  createParam(OdinFPErrorMessage,       asynParamOctet, &mFPErrorMessage);

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
  // Fetch status items
  this->fetchParams();
  if (!mAPI.connected()){
    setIntegerParam(ADStatus, ADStatusDisconnected);
    setStringParam(ADStatusMessage, "Unable to connect to Odin Server");
  } else {
    int status = 0;
    getIntegerParam(ADStatus, &status);
    if (status == ADStatusDisconnected){
      setIntegerParam(ADStatus, ADStatusIdle);
    }
    // Check for any errors from the odin server
    for (size_t index = 0; index != mODCount; ++index) {
      std::string error_msg = mAPI.readError(index);
      setStringParam(index, mFPErrorMessage, error_msg.c_str());
      if (error_msg != ""){
        setIntegerParam(index, mFPErrorState, 1);
      } else {
        setIntegerParam(index, mFPErrorState, 0);
      }
    }

    // Check for any adapter errors
    // If we are connected to the server then all errors are generated by
    // the server itself.
    std::string error_msg = "";
    mErrorMessage->get(error_msg);
    setStringParam(ADStatusMessage, error_msg.c_str());
    if (error_msg != ""){
      setIntegerParam(ADStatus, ADStatusError);
    } else {
      setIntegerParam(ADStatus, ADStatusIdle);
    }

    // Get image dimensions
    std::vector<int> imageDims = mAPI.getImageDims(mDatasetName);
    status |= (int) setIntegerParam(mImageHeight, imageDims[0]);
    status |= (int) setIntegerParam(mImageWidth, imageDims[1]);

    std::vector<int> chunkDims = mAPI.getChunkDims(mDatasetName);
    status |= (int) setIntegerParam(mChunkDepth, chunkDims[0]);
    status |= (int) setIntegerParam(mChunkHeight, chunkDims[1]);
    status |= (int) setIntegerParam(mChunkWidth, chunkDims[2]);
  }

  std::vector<int> numCaptured(mODCount);
  mNumCaptured->get(numCaptured);
  setIntegerParam(mNumCapturedSum, std::accumulate(numCaptured.begin(), numCaptured.end(), 0));

  std::vector<bool> writing(mODCount);
  mWriting->get(writing);
  int any_writing = std::accumulate(writing.begin(), writing.end(), 0);
  setIntegerParam(mWritingAny, any_writing == 0 ? 0 : 1);
  int currently_writing;
  mCapture->get(currently_writing);
  if (currently_writing && !any_writing) {
    setIntegerParam(mCapture->getIndex(), 0);
  }

  std::vector<bool> timeoutActive(mODCount);
  mTimeoutActive->get(timeoutActive);
  setIntegerParam(mTimeoutActiveAny,
                  std::accumulate(timeoutActive.begin(), timeoutActive.end(), 0) == 0 ? 0 : 1);

  callParamCallbacks();
  return asynSuccess;
}

asynStatus OdinDataDriver::acquireStart()
{
  mAPI.startWrite();
  return asynSuccess;
}

asynStatus OdinDataDriver::acquireStop()
{
  mAPI.stopWrite();
  return asynSuccess;
}

int OdinDataDriver::configureImageDims(std::vector<int> imageDims)
{
  int status = 0;
  asynPrint(pasynUserSelf, ASYN_TRACE_FLOW,
            "Image Dimensions: [%d, %d]\n", imageDims[0], imageDims[1]);

  status |= mAPI.setImageDims(mDatasetName, imageDims);
  return status;
}

int OdinDataDriver::configureChunkDims(std::vector<int> chunkDims)
{
  int status = 0;
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
      acquireStart();
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
  else if (function == mImageHeight){
    std::vector<int> imageDims(2);
    imageDims[0] = value;
    getIntegerParam(mImageWidth, &imageDims[1]);
    configureImageDims(imageDims);
  }
  else if (function == mImageWidth) {
    std::vector<int> imageDims(2);
    getIntegerParam(mImageHeight, &imageDims[0]);
    imageDims[1] = value;
    configureImageDims(imageDims);
  }
  else if (function == mChunkDepth){
    std::vector<int> chunkDims(3);
    chunkDims[0] = value;
    getIntegerParam(mChunkHeight, &chunkDims[1]);
    getIntegerParam(mChunkWidth, &chunkDims[2]);
    configureChunkDims(chunkDims);
  }
  else if (function == mChunkHeight){
    std::vector<int> chunkDims(3);
    getIntegerParam(mChunkDepth, &chunkDims[0]);
    chunkDims[1] = value;
    getIntegerParam(mChunkWidth, &chunkDims[2]);
    configureChunkDims(chunkDims);
  }
  else if (function == mChunkWidth) {
    std::vector<int> chunkDims(3);
    getIntegerParam(mChunkDepth, &chunkDims[0]);
    getIntegerParam(mChunkHeight, &chunkDims[1]);
    chunkDims[2] = value;
    configureChunkDims(chunkDims);
  }
  else if (RestParam * p = this->getParamByIndex(function)) {
    if (function == mCapture->getIndex()){
      p->put((bool)value);
    } else if (function == mStartCloseTimeout->getIndex()) {
      p->put((bool)value);
    }
    else {
      int address = -1;
      p->put(value, address);
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

  if (RestParam * p = this->getParamByIndex(function)) {
    int address = -1;
    status |= p->put(value, address);
  }
  if(function < mFirstParam) {
    status |= ADDriver::writeOctet(pasynUser, value, nChars, nActual);
  }

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
  for (int index = 0; index < (int) mODCount; index++){
    status |= (int) ADDriver::callParamCallbacks(index);
  }
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

  status = this->dynamicParam(pasynUser, drvInfo, pptypeName, psize, SSAdapterRoot);

  if (status == asynSuccess) {
    // Now return baseclass result
    status = ADDriver::drvUserCreate(pasynUser, drvInfo, pptypeName, psize);
  }
  return status;
}

extern "C" int odinDataDriverConfig(const char* portName, const char* serverPort,
                                    int odinServerPort, int odinDataCount,
                                    const char* datasetName, const char* detectorName,
                                    int maxBuffers, size_t maxMemory, int priority, int stackSize) {
  new OdinDataDriver(portName, serverPort,
                     odinServerPort, odinDataCount,
                     datasetName, detectorName,
                     maxBuffers, maxMemory, priority, stackSize);
  return asynSuccess;
}

// Code for iocsh registration
static const iocshArg odinDataDriverConfigArg0 = {"Port name", iocshArgString};
static const iocshArg odinDataDriverConfigArg1 = {"Server host name", iocshArgString};
static const iocshArg odinDataDriverConfigArg2 = {"Odin server port", iocshArgInt};
static const iocshArg odinDataDriverConfigArg3 = {"Number of OdinData processes", iocshArgInt};
static const iocshArg odinDataDriverConfigArg4 = {"Name of dataset", iocshArgString};
static const iocshArg odinDataDriverConfigArg5 = {"Detector name", iocshArgString};
static const iocshArg odinDataDriverConfigArg6 = {"maxBuffers", iocshArgInt};
static const iocshArg odinDataDriverConfigArg7 = {"maxMemory", iocshArgInt};
static const iocshArg odinDataDriverConfigArg8 = {"priority", iocshArgInt};
static const iocshArg odinDataDriverConfigArg9 = {"stackSize", iocshArgInt};

static const iocshArg *const odinDataDriverConfigArgs[] = {
    &odinDataDriverConfigArg0, &odinDataDriverConfigArg1,
    &odinDataDriverConfigArg2, &odinDataDriverConfigArg3,
    &odinDataDriverConfigArg4, &odinDataDriverConfigArg5,
    &odinDataDriverConfigArg6, &odinDataDriverConfigArg7,
    &odinDataDriverConfigArg8, &odinDataDriverConfigArg9};

static const iocshFuncDef configOdinDataDriver = {"odinDataDriverConfig", 9, odinDataDriverConfigArgs};

static void configOdinDataDriverCallFunc(const iocshArgBuf *args) {
  odinDataDriverConfig(args[0].sval, args[1].sval,
                       args[2].ival, args[3].ival,
                       args[4].sval, args[5].sval,
                       args[6].ival, args[7].ival, args[8].ival, args[9].ival);
}

static void odinDataDriverRegister() {
  iocshRegister(&configOdinDataDriver, configOdinDataDriverCallFunc);
}

extern "C" {
epicsExportRegistrar(odinDataDriverRegister);
}

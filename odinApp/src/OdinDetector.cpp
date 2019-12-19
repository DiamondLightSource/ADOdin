#include "OdinDetector.h"

#include <sstream>
#include <numeric>
#include <algorithm>

// EPICS includes
#include <epicsThread.h>
#include <epicsEvent.h>
#include <epicsString.h>
#include <drvSup.h>
#include <epicsExport.h>
#include <iocsh.h>

static const char *driverName = "OdinDetector";

/**
 * Function to run the receive thread in a separate thread in C++
 */
static void odinLiveViewListenerTaskC(void *oPtr)
{
  OdinDetector *ptr = (OdinDetector *)oPtr;
  ptr->live_view_task();
}


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

    : OdinClient(portName, serverHostname, odinServerPort,
                 detectorName, maxBuffers,
                 maxMemory, priority, stackSize),
    mAPI(detectorName, serverHostname, odinServerPort)
{
  strncpy(mHostname, serverHostname, sizeof(mHostname));

  // Register the detector API with the Odin client parent
  this->registerAPI(&mAPI);

  createDetectorParams();
  this->fetchParams();

  // Create the thread that runs the live image monitoring
  int status = (epicsThreadCreate("LiveViewTask",
                                  epicsThreadPriorityMedium,
                                  epicsThreadGetStackSize(epicsThreadStackMedium),
                                  (EPICSTHREADFUNC)odinLiveViewListenerTaskC,
                                  this) == NULL);
  if (status){
    setStringParam(ADStatusMessage, "epicsTheadCreate failure for image task\n");
  }
}

int OdinDetector::createDetectorParams()
{
  //mConnected = createRESTParam(OdinDetectorConnected, REST_P_BOOL, SSDetectorStatus, "connected");
  mAPIVersion = createRESTParam(OdinRestAPIVersion, REST_P_STRING, SSDetector, "api");
  // Create a parameter to store any error message from the Odin server
  mErrorMessage = createRESTParam("ERR_MESSAGE", REST_P_STRING, SSDetector, "status/error");
  mFirstParam = mAPIVersion->getIndex();

  // Create the parameter to store the Live View endpoint
  createParam(OdinDetectorLVEndpoint, asynParamOctet,   &mLiveViewEndpoint);

  // Bind the num_images parameter to NIMAGES asyn parameter
  mNumImages = createRESTParam(ADNumImagesString, REST_P_INT, SSDetector, "config/num_images");
  // Bind the exposure time parameter to
  createRESTParam(ADAcquireTimeString, REST_P_DOUBLE, SSDetector, "config/exposure_time");
  // Bind the detector details
  createRESTParam(ADManufacturerString, REST_P_STRING, SSDetector, "status/manufacturer");
  createRESTParam(ADModelString, REST_P_STRING, SSDetector, "status/model");
  // Bind the sensor size parameters
  createRESTParam(ADMaxSizeXString, REST_P_INT, SSDetector, "status/sensor/width");
  createRESTParam(ADMaxSizeYString, REST_P_INT, SSDetector, "status/sensor/height");
  createRESTParam(NDArraySizeXString, REST_P_INT, SSDetector, "status/sensor/width");
  createRESTParam(NDArraySizeYString, REST_P_INT, SSDetector, "status/sensor/height");
  createRESTParam(NDArraySizeString, REST_P_INT, SSDetector, "status/sensor/bytes");

  // Create a parameter to store the acquisition complete status
  mAcqComplete = createRESTParam("ACQ_COMPLETE", REST_P_BOOL, SSDetector, "status/acquisition_complete");

  // Create a parameter to store the state of the detector
  mDetectorState = createRESTParam("DETECTOR_STATE", REST_P_INT, SSDetector, "status/state");

  return 0;
}

void OdinDetector::live_view_task()
{
  bool frame_ready = false;
  int arrayCallbacks = 0;
  NDArray *pImage;
  epicsTimeStamp frameTime;
  this->lock();
  while(1){
    this->unlock();
    // Check to see if an image has been received
    frame_ready = mLV.listen_for_frame(2000);
    this->lock();

    if (frame_ready) {
        // Image has been received, so process it
        ImageDescription img = mLV.read_full_image();
        // Check we don't have a backlog of frames, we only want the most recent
        while (mLV.listen_for_frame(0)){
            img = mLV.read_full_image();
        }

        // Only forward the image if it is considered valid
        if (img.valid) {
          // Allocate NDArray memory
          size_t dims[2] = {img.width, img.height};
          // Convert the datatype into an ND datatype
          NDDataType_t dtype = NDUInt8;
          if (img.dtype == "uint8") {
            dtype = NDUInt8;
          } else if (img.dtype == "uint16") {
            dtype = NDUInt16;
          } else if (img.dtype == "uint32") {
            dtype = NDUInt32;
          } else if (img.dtype == "float") {
            dtype = NDFloat32;
          }
          pImage = this->pNDArrayPool->alloc(2, dims, dtype, 0, NULL);
          if (pImage) {
            pImage->dims[0].size = dims[0];
            pImage->dims[1].size = dims[1];
            pImage->uniqueId = img.number;
            epicsTimeGetCurrent(&frameTime);
            pImage->timeStamp = frameTime.secPastEpoch + frameTime.nsec / 1.e9;
            memcpy(pImage->pData, img.dPtr, img.bytes);

            // Get any attributes that have been defined for this driver
            this->getAttributes(pImage->pAttributeList);

            getIntegerParam(NDArrayCallbacks, &arrayCallbacks);

            if (arrayCallbacks) {
              // Must release the lock here, or we can get into a deadlock, because we can
              // block on the plugin lock, and the plugin can be calling us
              this->unlock();
              doCallbacksGenericPointer(pImage, NDArrayData, 0);
              this->lock();
            }

            // Free the image buffer
            pImage->release();
          }
        }
    }
  }
}

asynStatus OdinDetector::getStatus()
{
  int status = 0;
  int acquiring = 0;

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

    // Check if we have initiated an acquisition
    getIntegerParam(ADAcquire, &acquiring);
    if (acquiring){
      // Now fetch the current acquisition status
      bool acq_state = false;
      mAcqComplete->get(acq_state);
      // We are in an acquisition, check the status
      if (acq_state){
        // The acquisition has completed, reset the status
        setIntegerParam(ADAcquire, 0);
        setStringParam(ADStatusMessage, "Acquisition has completed");
        setIntegerParam(ADStatus, ADStatusIdle);
      } else {
        setStringParam(ADStatusMessage, "Acquiring...");
      }
      callParamCallbacks();
    } else {
      // Set the state from the detector adapter.  A non-standard state
      // can be set here.  This will be overidden by any error messages below
      int det_state = 0;
      int current_state = 0;
      getIntegerParam(ADStatus, &current_state);
      mDetectorState->get(det_state);
      if (!(current_state == ADStatusAborted && det_state == ADStatusIdle)){
        setIntegerParam(ADStatus, det_state);
      }
    }

    // Check for any errors
    // If we are connected to the server then all errors are generated by
    // the server itself.
    std::string error_msg = "";
    mErrorMessage->get(error_msg);
    setStringParam(ADStatusMessage, error_msg.c_str());
    if (error_msg != ""){
      setIntegerParam(ADStatus, ADStatusError);
    } else if (status == ADStatusError){
      setIntegerParam(ADStatus, ADStatusIdle);
    }
  }

  if(status) {
    return asynError;
  }

  callParamCallbacks();
  return asynSuccess;
}

asynStatus OdinDetector::acquireStart()
{
  mAPI.startAcquisition();
  return asynSuccess;
}

asynStatus OdinDetector::acquireStop()
{
  mAPI.stopAcquisition();
  return asynSuccess;
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
  else if (RestParam * p = this->getParamByIndex(function)) {
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

  if (RestParam * p = this->getParamByIndex(function)) {
    status |= p->put(value);
  }
  if (status) {
    asynPrint(pasynUser, ASYN_TRACE_ERROR,
              "%s:%s error returned from put, status=%d function=%d, value=%f\n",
              driverName, functionName, status, function, value);
  }

  if(function < mFirstParam) {
    status |= ADDriver::writeFloat64(pasynUser, value);
  }

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

  if (RestParam * p = this->getParamByIndex(function)) {
    status |= p->put(value);
  }

  if (function == mLiveViewEndpoint) {
      setStringParam(mLiveViewEndpoint, value);
      mLV.connect(value);
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
  for (int index = 0; index < 10; index++){
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
void OdinDetector::report(FILE *fp, int details) {
  // Invoke the base class method
  ADDriver::report(fp, details);
}

asynStatus OdinDetector::drvUserCreate(asynUser *pasynUser,
                                       const char *drvInfo,
                                       const char **pptypeName,
                                       size_t *psize)
{
  asynStatus status = asynSuccess;

  status = this->dynamicParam(pasynUser, drvInfo, pptypeName, psize, SSDetector);

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

#include "odinDetector.h"

#include <epicsExport.h>
#include <iocsh.h>

static const std::string DRIVER_VERSION("0-1");

static const char *driverName = "odinDetector";

/* Constructor for Odin driver; most parameters are simply passed to
 * ADDriver::ADDriver.
 * After calling the base class constructor this method creates a thread to
 * collect the detector data, and sets reasonable default values for the
 * parameters defined in this class, asynNDArrayDriver, and ADDriver.
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
odinDetector::odinDetector(const char *portName, const char *serverHostname,
                           int maxBuffers, size_t maxMemory, int priority,
                           int stackSize)

    : ADDriver(portName, 2, 0, maxBuffers, maxMemory,
               0, 0,                 /* No interfaces beyond ADDriver.cpp */
               ASYN_CANBLOCK |       /* ASYN_CANBLOCK=1 */
                   ASYN_MULTIDEVICE, /* ASYN_MULTIDEVICE=1 */
               1,                    /* autoConnect=1 */
               priority, stackSize) {
  const char *functionName = "odinDetector";

  // Write version to appropriate parameter
  setStringParam(NDDriverVersion, DRIVER_VERSION);
}

/* Called when asyn clients call pasynInt32->write().
 * This function performs actions for some parameters, including ADAcquire,
 * ADTriggerMode, etc.
 * For all parameters it sets the value in the parameter library and calls any
 * registered callbacks..
 * \param[in] pasynUser pasynUser structure that encodes the reason and address.
 * \param[in] value Value to write.
 */
asynStatus odinDetector::writeInt32(asynUser *pasynUser, epicsInt32 value) {
  int function = pasynUser->reason;
  asynStatus status = asynSuccess;
  const char *functionName = "writeInt32";

  status = ADDriver::writeInt32(pasynUser, value);

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
asynStatus odinDetector::writeFloat64(asynUser *pasynUser,
                                      epicsFloat64 value) {
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
asynStatus odinDetector::writeOctet(asynUser *pasynUser, const char *value,
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
void odinDetector::report(FILE *fp, int details) {
  // Invoke the base class method
  ADDriver::report(fp, details);
}

asynStatus odinDetector::drvUserCreate(asynUser *pasynUser,
                                       const char *drvInfo,
                                       const char **pptypeName,
                                       size_t *psize) {
  return ADDriver::drvUserCreate(pasynUser, drvInfo, pptypeName, psize);
}

extern "C" int odinDetectorConfig(const char *portName,
                                  const char *serverPort,
                                  int maxBuffers,
                                  size_t maxMemory,
                                  int priority,
                                  int stackSize) {
  new odinDetector(portName, serverPort, maxBuffers, maxMemory, priority,
                   stackSize);
  return asynSuccess;
}

// Code for iocsh registration
static const iocshArg odinDetectorConfigArg0 = {"Port name", iocshArgString};
static const iocshArg odinDetectorConfigArg1 = {"Server host name",
                                                iocshArgString};
static const iocshArg odinDetectorConfigArg2 = {"maxBuffers", iocshArgInt};
static const iocshArg odinDetectorConfigArg3 = {"maxMemory", iocshArgInt};
static const iocshArg odinDetectorConfigArg4 = {"priority", iocshArgInt};
static const iocshArg odinDetectorConfigArg5 = {"stackSize", iocshArgInt};
static const iocshArg *const odinDetectorConfigArgs[] = {
    &odinDetectorConfigArg0, &odinDetectorConfigArg1,
    &odinDetectorConfigArg2, &odinDetectorConfigArg3,
    &odinDetectorConfigArg4, &odinDetectorConfigArg5};

static const iocshFuncDef configOdinDetector = {"odinDetectorConfig",
                                                6, odinDetectorConfigArgs};

static void configOdinDetectorCallFunc(const iocshArgBuf *args) {
  odinDetectorConfig(args[0].sval, args[1].sval, args[2].ival,
                     args[3].ival, args[4].ival, args[5].ival);
}

static void odinDetectorRegister(void) {
  iocshRegister(&configOdinDetector, configOdinDetectorCallFunc);
}

extern "C" {
  epicsExportRegistrar(odinDetectorRegister);
}

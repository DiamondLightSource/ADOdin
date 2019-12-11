/*
 * OdinClient.cpp
 *
 *  Created on: 21 Feb 2018
 *      Author: gnx91527
 */

#include "OdinClient.h"

#include <sstream>
#include <epicsString.h>

// These parameters are optionally configured by ioc init commands
//std::string                  OdinDetector::mOdinDataLibraryPath = "";
//std::vector<ODConfiguration> OdinDetector::mODConfig                ;
//size_t                       OdinDetector::mODCount             =  0;
//std::string                  OdinDetector::mDatasetName         = "";
//std::string                  OdinClient::mProcessPluginName   = "";
//std::string                  OdinDetector::mDetectorLibraryPath = "";

static const std::string DRIVER_VERSION("0-1");
static const char *driverName = "OdinDetector";


OdinClient::OdinClient(const char * portName,
                       const char * serverHostname,
                       int odinServerPort,
                       const char * detectorName,
                       int maxBuffers,
                       size_t maxMemory,
                       int priority,
                       int stackSize) :
  ADDriver(portName, 10, 0, maxBuffers, maxMemory,
           asynEnumMask, asynEnumMask,    /* Add Enum interface */
           ASYN_CANBLOCK |                /* ASYN_CANBLOCK=1 */
           ASYN_MULTIDEVICE,          /* ASYN_MULTIDEVICE=1 */
           1,                             /* autoConnect=1 */
           priority, stackSize),
  mFirstParam(0),
  mAPIVersion(0),
  mAPI(0),
  mParams(0)
{
  // Write version to appropriate parameter
  setStringParam(NDDriverVersion, DRIVER_VERSION);
}

void OdinClient::registerAPI(OdinRestAPI *api)
{
  mAPI = api;
  mParams = new RestParamSet(this, mAPI, pasynUserSelf);
}

RestParam * OdinClient::createRESTParam(const std::string& asynName, rest_param_type_t restType,
                                        sys_t subSystem, const std::string& name,
                                        size_t arraySize)
{
  RestParam * p = 0;
  if (mAPI){
    p = mParams->create(asynName, restType, mAPI->sysStr(subSystem), name, arraySize);
  }
  return p;
}

asynStatus OdinClient::dynamicParam(asynUser *pasynUser,
                                    const char *drvInfo,
                                    const char **pptypeName,
                                    size_t *psize,
                                    sys_t subsystem)
{
  static const char *functionName = "drvUserCreate";
  asynStatus status = asynSuccess;
  int index;
  RestParam * generatedParam;
  int arraySize = 0;
  std::string value;
  char * httpRequest = 0;

  // Accepted parameter formats for HTTP parameters
  //
  // _ODI_...  => Integer parameter
  // _ODE_...  => Enum parameter
  // _ODS_...  => String parameter
  // _ODD_...  => Double parameter
  // _ODIn_... => Array size n of Integer parameter
  // _ODEn_... => Array size n of Enum parameter
  // _ODSn_... => Array size n of String parameter
  // _ODDn_... => Array size n of Double parameter
  if (findParam(drvInfo, &index) && strlen(drvInfo) > 5 && strncmp(drvInfo, "_OD", 2) == 0 &&
      (drvInfo[4] == '_' or drvInfo[5] == '_')) {
    // Decide if the parameter is an array
    if (drvInfo[5] == '_'){
      // drvInfo[4] contains the array size for this parameter
      arraySize = drvInfo[4] - '0';
    }

    // Retrieve the name of the variable
    if (arraySize == 0){
      httpRequest = epicsStrDup(drvInfo + 5);
    } else {
      httpRequest = epicsStrDup(drvInfo + 6);
    }

    std::stringstream temp;
    temp << httpRequest;
    std::string uri = temp.str();
    std::string name;
    name = uri.substr(uri.rfind("/" + 1));

    RestParam * existingParam = mParams->getByName(drvInfo);
    if (existingParam == NULL || existingParam->getName() != name) {
      // If param doesn't already exist -- Create it
      // If param does already exist and is bound the the same URI
      // -- Ignore - this is probably the *_RBV record
      // If param does already exist, but it is bound to a different URI
      // -- Let it try to create it and throw an exception, as it would if manually created

      asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                "%s:%s: Creating new parameter with URI: %s\n",
                driverName, functionName, httpRequest);
      // Check for I, D or S in drvInfo[3]
      switch (drvInfo[3]) {
      case 'I':
        // Create the parameter
        asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                  "%s:%s: Integer parameter: %s\n",
                  driverName, functionName, drvInfo);
        generatedParam = createRESTParam(drvInfo, REST_P_INT, subsystem, httpRequest, arraySize);
        generatedParam->fetch();
        // Store the parameter
        break;
      case 'E':
        // Create the parameter
        asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                  "%s:%s: Enum parameter: %s\n",
                  driverName, functionName, drvInfo);
        generatedParam = createRESTParam(drvInfo, REST_P_ENUM, subsystem, httpRequest, arraySize);
        generatedParam->fetch();
        // Store the parameter
        break;
        case 'D':
          // Create the parameter
          asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                    "%s:%s: Double parameter: %s\n",
                    driverName, functionName, drvInfo);
          generatedParam = createRESTParam(drvInfo, REST_P_DOUBLE, subsystem, httpRequest, arraySize);
          generatedParam->fetch();
          // Store the parameter
          break;
        case 'S':
          // Create the parameter
          asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                    "%s:%s: String parameter: %s\n",
                    driverName, functionName, drvInfo);
          generatedParam = createRESTParam(drvInfo, REST_P_STRING, subsystem, httpRequest, arraySize);
          generatedParam->fetch();
          // Store the parameter
          break;
        case 'B':
          // Create the parameter
          asynPrint(this->pasynUserSelf, ASYN_TRACE_FLOW,
                    "%s:%s: String parameter: %s\n",
                    driverName, functionName, drvInfo);
          generatedParam = createRESTParam(drvInfo, REST_P_BOOL, subsystem, httpRequest, arraySize);
          generatedParam->fetch();
          // Store the parameter
          break;
        default:
          asynPrint(this->pasynUserSelf, ASYN_TRACE_ERROR,
                    "%s:%s: Expected _ODx_... where x is one of I, D or S. Got '%c'\n",
                    driverName, functionName, drvInfo[3]);
          status = asynError;
      }
    }
  }
  return status;
}

int OdinClient::fetchParams()
{
  return mParams->fetchAll();
}

RestParam *OdinClient::getParamByIndex(int index)
{
  return mParams->getByIndex(index);
}

OdinClient::~OdinClient() {
  // TODO Auto-generated destructor stub
}


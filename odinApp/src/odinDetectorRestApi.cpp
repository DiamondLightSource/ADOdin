#include "odinDetectorRestApi.h"

#include <stdexcept>
#include <algorithm>
#include <stdlib.h>

#include "jsonDict.h"
#include "odinDataConfig.h"


const std::string OdinDetectorRestAPI::CONNECT           = "connect";
const std::string OdinDetectorRestAPI::START_ACQUISITION = "start_acquisition";
const std::string OdinDetectorRestAPI::STOP_ACQUISITION  = "stop_acquisition";


OdinDetectorRestAPI::OdinDetectorRestAPI(const std::string& detectorName,
                                         const std::string& hostname,
                                         int port,
                                         size_t numSockets) :
    OdinRestAPI(hostname, port, numSockets),
    mDetectorName(detectorName)
{
  const std::string api = "/api/" API_VERSION "/";

  sysStr_[SSDetector]             = api + detectorName + "/";
  sysStr_[SSDetectorConfig]       = api + detectorName + "/config/";
  sysStr_[SSDetectorStatus]       = api + detectorName + "/status/";
  sysStr_[SSDetectorCommand]      = api + detectorName + "/command/";
}

int OdinDetectorRestAPI::connectDetector()
{
  JsonDict stateDict = JsonDict("state", true);
  JsonDict connect = JsonDict("connect", stateDict);
  return put(sysStr(SSDetectorCommand), CONNECT, connect.str());
}

int OdinDetectorRestAPI::disconnectDetector()
{
  JsonDict stateDict = JsonDict("state", false);
  JsonDict connect = JsonDict("connect", stateDict);
  return put(sysStr(SSDetectorCommand), CONNECT, connect.str());
}

int OdinDetectorRestAPI::startAcquisition()
{
  return put(sysStr(SSDetectorCommand), START_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinDetectorRestAPI::stopAcquisition()
{
  return put(sysStr(SSDetectorCommand), STOP_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinDetectorRestAPI::lookupAccessMode(std::string subSystem, rest_access_mode_t& accessMode)
{
    long ssEnum = std::distance(sysStr_, std::find(sysStr_, sysStr_ + SSCount, subSystem));

    switch(ssEnum)
    {
      case SSDetector:
        accessMode = REST_ACC_RW;
        return EXIT_SUCCESS;
      case SSDetectorStatus:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      case SSDetectorCommand:
        accessMode = REST_ACC_WO;
        return EXIT_SUCCESS;
      default:
        return OdinRestAPI::lookupAccessMode(subSystem, accessMode);
    }
}

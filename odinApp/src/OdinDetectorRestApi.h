#ifndef ODIN_DETECTOR_REST_API_H
#define ODIN_DETECTOR_REST_API_H

#include <map>
#include <string>
#include <epicsMutex.h>
#include <osiSock.h>

#include "OdinRestApi.h"
#include "restParam.h"

#include "OdinDataConfig.h"


class OdinDetectorRestAPI : public OdinRestAPI
{
 public:
  const std::string mDetectorName;
  int lookupAccessMode(std::string subSystem, rest_access_mode_t &accessMode);

  OdinDetectorRestAPI(const std::string& detectorName,
                      const std::string& hostname,
                      int port,
                      size_t numSockets=5);

  int connectDetector();
  int disconnectDetector();
  int startAcquisition();
  int stopAcquisition();

 private:
  static const std::string CONNECT;
  static const std::string START_ACQUISITION;
  static const std::string STOP_ACQUISITION;
};

#endif

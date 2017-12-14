#ifndef ODIN_REST_API_H
#define ODIN_REST_API_H

#include <map>
#include <string>
#include <epicsMutex.h>
#include <osiSock.h>

#include "restApi.h"
#include "restParam.h"

// Subsystems
typedef enum
{
  SSRoot,
  SSAdapters,
  SSDetector,
  SSDetectorStatus,
  SSDetectorCommand,
  SSData,

  SSCount,
} sys_t;

class OdinRestAPI : public RestAPI
{
 public:
  static const char *sysStr [SSCount];
  int lookupAccessMode(std::string subSystem, rest_access_mode_t &accessMode);

  OdinRestAPI(std::string const & hostname, int port, size_t numSockets=5);

  int connectDetector();
  int disconnectDetector();
  int startAcquisition();
  int stopAcquisition();
  int loadFileWriter(std::string odinDataPath);

 private:
  static const std::string CONNECT;
  static const std::string START_ACQUISITION;
  static const std::string STOP_ACQUISITION;
  static const std::string EMPTY_JSON_STRING;
};

#endif

#ifndef ODIN_REST_API_H
#define ODIN_REST_API_H

#include <map>
#include <string>
#include <epicsMutex.h>
#include <osiSock.h>

#include "restApi.h"
#include "restParam.h"

#include "odinDataConfig.h"

// REST Strings
#define API_VERSION              "0.1"

// Subsystems
typedef enum
{
  SSRoot,
  SSAdapters,
  SSDetector,
  SSDetectorConfig,
  SSDetectorStatus,
  SSDetectorCommand,
  SSDataFWStatus,
  SSDataFWStatusDetector,
  SSDataFWStatusHDF,
  SSDataRoot,
  SSDataFWConfig,
  SSDataFWConfigDetector,
  SSDataFWConfigHDF,
  SSDataFWConfigHDFProcess,
  SSDataFWConfigHDFDataset,
  SSDataFRConfig,
  SSDataFRStatus,

  SSCount
} sys_t;


class OdinRestAPI : public RestAPI
{
 public:
  std::string sysStr(sys_t sys);
  int lookupAccessMode(std::string subSystem, rest_access_mode_t &accessMode);

  OdinRestAPI(const std::string& hostname,
              int port,
              size_t numSockets=5);

  bool connected();
  virtual ~OdinRestAPI(){};

protected:
  std::string sysStr_[SSCount];
  static const std::string EMPTY_JSON_STRING;

};

#endif

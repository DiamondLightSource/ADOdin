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
  int loadPlugin(const std::string& modulePath,
                 const std::string& name, const std::string& index, const std::string& library);
  int loadProcessPlugin(const std::string& modulePath, const std::string& pluginIndex);
  int loadFileWriterPlugin(const std::string& odinDataPath);
  int connectPlugins(const std::string& index, const std::string& connection);
  int connectToFrameReceiver(const std::string& index);
  int connectToProcessPlugin(const std::string& index);

  static const std::string FILE_WRITER_PLUGIN;

 private:
  static const std::string CONNECT;
  static const std::string START_ACQUISITION;
  static const std::string STOP_ACQUISITION;
  static const std::string EMPTY_JSON_STRING;
};

#endif

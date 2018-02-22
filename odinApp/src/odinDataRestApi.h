#ifndef ODIN_DATA_REST_API_H
#define ODIN_DATA_REST_API_H

#include <map>
#include <string>
#include <epicsMutex.h>
#include <osiSock.h>

#include "odinRestApi.h"
#include "restParam.h"

#include "odinDataConfig.h"


class OdinDataRestAPI : public OdinRestAPI
{
 public:
  const std::string mPluginName;
  int lookupAccessMode(std::string subSystem, rest_access_mode_t &accessMode);

  OdinDataRestAPI(const std::string& hostname,
                  const std::string& pluginName,
                  int port,
                  size_t numSockets=5);

  // OdinData Methods
  // -- Initialisation
  int configureSharedMemoryChannels(ODConfiguration config);
  int loadPlugin(const std::string& modulePath,
                 const std::string& name, const std::string& index, const std::string& library);
  int loadProcessPlugin(const std::string& modulePath, const std::string& pluginIndex);
  int loadFileWriterPlugin(const std::string& odinDataPath);
  int connectPlugins(const std::string& index, const std::string& connection);
  int connectToFrameReceiver(const std::string& index);
  int connectToProcessPlugin(const std::string& index);
  // -- Acquisition Control
  int createFile(const std::string& name, const std::string& path);
  int createDataset(const std::string& name);
  int setImageDims(const std::string& datasetName, std::vector<int>& imageDims);
  int setChunkDims(const std::string& datasetName, std::vector<int>& chunkDims);
  int startWrite();
  int stopWrite();

  static const std::string FILE_WRITER_PLUGIN;

 private:
  std::string mProcessPluginIndex;
};

#endif

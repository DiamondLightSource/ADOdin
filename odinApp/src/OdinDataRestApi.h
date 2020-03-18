#ifndef ODIN_DATA_REST_API_H
#define ODIN_DATA_REST_API_H

#include <map>
#include <string>
#include <epicsMutex.h>
#include <osiSock.h>

#include "OdinRestApi.h"
#include "restParam.h"

#define ERROR_REFRESH_TIME 3  // Seconds

class OdinDataRestAPI : public OdinRestAPI
{
 public:
  const std::string mPluginName;
  int lookupAccessMode(std::string subSystem, rest_access_mode_t &accessMode);

  OdinDataRestAPI(const std::string& hostname,
                  const std::string& pluginName,
                  int port,
                  size_t odinDataCount,
                  size_t numSockets=5);

  // OdinData Methods
  int setImageDims(const std::string& datasetName, std::vector<int>& imageDims);
  std::vector<int> getImageDims(const std::string& datasetName);
  int setChunkDims(const std::string& datasetName, std::vector<int>& chunkDims);
  std::vector<int> getChunkDims(const std::string& datasetName);
  std::string readError(size_t address);
  int startWrite();
  int stopWrite();

 private:
  std::vector<size_t> mErrorCycle;
};

#endif

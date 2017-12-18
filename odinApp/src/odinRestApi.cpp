#include "odinRestApi.h"

#include <stdexcept>

#include <stdlib.h>
#include <algorithm>
#include <frozen.h>     // JSON parser

#include "jsonDict.h"

#define API_VERSION              "0.1"

// JSON Strings
#define PLUGIN                   "plugin"
#define LOAD                     "load"
#define PLUGIN_INDEX             "index"
#define PLUGIN_NAME              "name"
#define PLUGIN_LIBRARY           "library"
#define DETECTOR_PLUGIN_INDEX    "excalibur"
#define ODIN_DATA_PLUGIN_INDEX   "odin_data"
#define FILE_WRITER_PLUGIN_INDEX "hdf"
#define FILE_WRITER_CLASS        "FileWriterPlugin"
#define FILE_WRITER_LIB          "libHdf5Plugin.so"
#define ODIN_DATA_LIB_PATH       "prefix/lib"

#define EOL                     "\r\n"      // End of Line
#define EOL_LEN                 2           // End of Line Length
#define EOH                     EOL EOL     // End of Header
#define EOH_LEN                 (EOL_LEN*2) // End of Header Length


#define DATA_NATIVE             "application/json"

#define MAX_HTTP_RETRIES        1
#define MAX_MESSAGE_SIZE        512
#define MAX_BUF_SIZE            256
#define MAX_JSON_TOKENS         100

#define ERR_PREFIX  "OdinRestAPI"
#define ERR(msg) fprintf(stderr, ERR_PREFIX "::%s: %s\n", functionName, msg)

#define ERR_ARGS(fmt,...) fprintf(stderr, ERR_PREFIX "::%s: " fmt "\n", \
    functionName, __VA_ARGS__)

// Requests

#define REQUEST_GET\
    "GET %s%s HTTP/1.1" EOL \
    "Host: %s" EOL\
    "Content-Length: 0" EOL \
    "Accept: " DATA_NATIVE EOH

#define REQUEST_PUT\
    "PUT %s%s HTTP/1.1" EOL \
    "Host: %s" EOL\
    "Accept-Encoding: identity" EOL\
    "Content-Type: " DATA_NATIVE EOL \
    "Content-Length: %lu" EOH

#define REQUEST_DELETE\
    "DELETE %s%s HTTP/1.1" EOL\
    "Host: %s" EOH

// Static public members

const std::string OdinRestAPI::CONNECT           = "connect";
const std::string OdinRestAPI::START_ACQUISITION = "start_acquisition";
const std::string OdinRestAPI::STOP_ACQUISITION  = "stop_acquisition";
const std::string OdinRestAPI::EMPTY_JSON_STRING = "\"\"";

const char *OdinRestAPI::sysStr [SSCount] = {
    "/",
    "/api/" API_VERSION "/adapters",
    "/api/" API_VERSION "/" DETECTOR_PLUGIN_INDEX "/",
    "/api/" API_VERSION "/" DETECTOR_PLUGIN_INDEX "/status/",
    "/api/" API_VERSION "/" DETECTOR_PLUGIN_INDEX "/command/",
    "/api/" API_VERSION "/" ODIN_DATA_PLUGIN_INDEX "/",
};


OdinRestAPI::OdinRestAPI(std::string const & hostname, int port, size_t numSockets) :
    RestAPI(hostname, port, numSockets) {}

int OdinRestAPI::connectDetector()
{
  return put(sysStr[SSDetectorCommand], CONNECT, "state", "true");
}

int OdinRestAPI::disconnectDetector()
{
  return put(sysStr[SSDetectorCommand], CONNECT, "state", "false");
}

int OdinRestAPI::startAcquisition()
{
  return put(sysStr[SSDetectorCommand], START_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinRestAPI::stopAcquisition()
{
  return put(sysStr[SSDetectorCommand], STOP_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinRestAPI::loadPlugin(const std::string& modulePath,
                            const char * name, const char * index, const char * library) {
  std::vector<JsonDict> loadConfig;
  std::stringstream fullPath;
  fullPath << modulePath << "/" << ODIN_DATA_LIB_PATH << "/" << library;

  loadConfig.push_back(JsonDict(PLUGIN_NAME, name));
  loadConfig.push_back(JsonDict(PLUGIN_INDEX, index));
  loadConfig.push_back(JsonDict(PLUGIN_LIBRARY, fullPath.str().c_str()));
  JsonDict loadDict = JsonDict(loadConfig);
  JsonDict config = JsonDict(LOAD, loadDict);

  return put(sysStr[SSData], PLUGIN, config.str());
}

int OdinRestAPI::loadProcessPlugin(const std::string& modulePath, const std::string& pluginIndex)
{
  std::stringstream sPluginName;
  sPluginName << pluginIndex << "ProcessPlugin";
  std::string pluginName = sPluginName.str();
  pluginName[0] = toupper(pluginName[0]);
  std::stringstream sLibrary;
  sLibrary << "lib" << pluginName << ".so";

  return loadPlugin(modulePath, pluginName.c_str(), pluginIndex.c_str(), sLibrary.str().c_str());
}

int OdinRestAPI::loadFileWriterPlugin(const std::string& odinDataPath)
{
  return loadPlugin(odinDataPath, FILE_WRITER_CLASS, FILE_WRITER_PLUGIN_INDEX, FILE_WRITER_LIB);
}

int OdinRestAPI::lookupAccessMode(
        std::string subSystem, rest_access_mode_t &accessMode)
{
    long ssEnum = std::distance(
            sysStr, std::find(sysStr, sysStr + SSCount, subSystem));
    switch(ssEnum)
    {
      case SSRoot: SSDetector: SSDetectorStatus:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      case SSDetectorCommand:
        accessMode = REST_ACC_WO;
        default:
          return EXIT_FAILURE;
    }
}

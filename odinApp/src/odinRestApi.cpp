#include "odinRestApi.h"

#include <stdexcept>

#include <stdlib.h>
#include <algorithm>
#include <frozen.h>     // JSON parser

#include "jsonDict.h"

#define API_VERSION             "0.1"
#define DETECTOR_NAME           "excalibur"
#define ODIN_DATA               "odin_data"
#define ODIN_DATA_LIB_PATH      "build/lib"
#define FILE_WRITER_CLASS       "FileWriterPlugin"
#define FILE_WRITER_LIB         "libHdf5Plugin.so"
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
    "/api/" API_VERSION "/" DETECTOR_NAME "/",
    "/api/" API_VERSION "/" DETECTOR_NAME "/status/",
    "/api/" API_VERSION "/" DETECTOR_NAME "/command/",
    "/api/" API_VERSION "/" ODIN_DATA "/",
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

int OdinRestAPI::loadFileWriter(std::string odinDataPath)
{
  std::vector<JsonDict> loadDict;
  std::stringstream libraryPath;
  libraryPath << odinDataPath << "/" << ODIN_DATA_LIB_PATH << "/" << FILE_WRITER_LIB;

  loadDict.push_back(JsonDict("library", libraryPath.str().c_str()));
  loadDict.push_back(JsonDict("index", "hdf"));
  loadDict.push_back(JsonDict("name", FILE_WRITER_CLASS));
  JsonDict loadConfig = JsonDict(loadDict);
  JsonDict config = JsonDict("load", loadConfig);

  return put(sysStr[SSData], "plugin", config.str());
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

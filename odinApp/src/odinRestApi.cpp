#include "odinRestApi.h"

#include <stdexcept>
#include <algorithm>

#include "jsonDict.h"
#include "odinDataConfig.h"


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
const std::string RestAPI::PARAM_ACCESS_MODE = "access";          // Set key for RestParam access mode
const std::string RestAPI::PARAM_ENUM_VALUES = "allowed_values";  // Set key for RestParam enum values
const std::string RestAPI::PARAM_VALUE       = "value";           // Set key for RestParam fetch response

const std::string OdinRestAPI::EMPTY_JSON_STRING = "";


OdinRestAPI::OdinRestAPI(const std::string& hostname,
                         int port,
                         size_t numSockets) :
    RestAPI(hostname, port, numSockets)
{
  const std::string api = "/api/" API_VERSION "/";

  sysStr_[SSRoot]                 = "/";
  sysStr_[SSAdapters]             = api + "/adapters";
}

bool OdinRestAPI::connected(){
  return (this->connectedSockets()>0);
}

std::string OdinRestAPI::sysStr(sys_t sys)
{
  return sysStr_[sys];
}

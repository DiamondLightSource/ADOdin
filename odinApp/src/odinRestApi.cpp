#include "odinRestApi.h"

#include <stdexcept>

#include <stdlib.h>
#include <algorithm>
#include <frozen.h>     // JSON parser

#define API_VERSION             "0.1"
#define DETECTOR_NAME           "excalibur"
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

const char *OdinRestAPI::sysStr [SSCount] = {
    "/api",
    "/api/" API_VERSION "/adapters",
    "/api/" API_VERSION "/" DETECTOR_NAME "/",
    "/api/" API_VERSION "/" DETECTOR_NAME "/status/",
};


OdinRestAPI::OdinRestAPI(std::string const & hostname, int port, size_t numSockets) :
    RestAPI(hostname, port, numSockets) {}

int OdinRestAPI::lookupAccessMode(
        std::string subSystem, rest_access_mode_t &accessMode)
{
    long ssEnum = std::distance(
            sysStr, std::find(sysStr, sysStr + SSCount, subSystem));
    switch(ssEnum)
    {
      case SSAPIVersion: SSExcalibur: SSExcaliburStatus:
            accessMode = REST_ACC_RO;
            return EXIT_SUCCESS;
        default:
            return EXIT_FAILURE;
    }
}

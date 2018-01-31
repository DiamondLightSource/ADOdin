#include "odinRestApi.h"

#include <stdexcept>
#include <algorithm>

#include "jsonDict.h"

// REST Strings
#define API_VERSION              "0.1"
#define ODIN_DATA_ADAPTER        "odin_data"

// OdinData JSON Strings
#define PLUGIN                      "plugin"
#define PLUGIN_LOAD                 "load"
#define PLUGIN_CONNECT              "connect"
#define PLUGIN_INDEX                "index"
#define PLUGIN_INDEX_FILE_WRITER    "hdf"
#define PLUGIN_INDEX_FRAME_RECEIVER "frame_receiver"
#define PLUGIN_CONNECTION           "connection"
#define PLUGIN_NAME                 "name"
#define PLUGIN_LIBRARY              "library"
#define FR_SETUP                    "fr_setup"
#define FR_READY_CNXN               "fr_ready_cnxn"
#define FR_RELEASE_CNXN             "fr_release_cnxn"
#define FILE_WRITER_CLASS           "FileWriterPlugin"
#define FILE_WRITER_LIB             "libHdf5Plugin.so"
#define ODIN_DATA_LIB_PATH          "prefix/lib"
#define FILE                        "file"
#define FILE_NAME                   "name"
#define FILE_PATH                   "path"
#define FILE_WRITE                  "write"
#define DATASET                     "dataset"
#define DATASET_CMD                 "cmd"
#define DATASET_CMD_CREATE          "create"
#define DATASET_NAME                "name"
#define DATASET_DATATYPE            "datatype"
#define DATASET_DIMS                "dims"
#define DATASET_CHUNKS              "chunks"

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

const std::string OdinRestAPI::CONNECT           = "connect";
const std::string OdinRestAPI::START_ACQUISITION = "start_acquisition";
const std::string OdinRestAPI::STOP_ACQUISITION  = "stop_acquisition";
const std::string OdinRestAPI::EMPTY_JSON_STRING = "\"\"";

const std::string OdinRestAPI::FILE_WRITER_PLUGIN = PLUGIN_INDEX_FILE_WRITER;


OdinRestAPI::OdinRestAPI(const std::string& detectorName,
                         const std::string& hostname,
                         const std::string& pluginName,
                         int port,
                         size_t numSockets) :
    RestAPI(hostname, port, numSockets),
    mDetectorName(detectorName),
    mPluginName(pluginName)
{
  const std::string api = "/api/" API_VERSION "/";

  sysStr_[SSRoot]                 = "/";
  sysStr_[SSAdapters]             = api + "/adapters";
  sysStr_[SSDetector]             = api + detectorName + "/";
  sysStr_[SSDetectorConfig]       = api + detectorName + "/config/";
  sysStr_[SSDetectorStatus]       = api + detectorName + "/status/";
  sysStr_[SSDetectorCommand]      = api + detectorName + "/command/";
  sysStr_[SSDataStatus]           = api + ODIN_DATA_ADAPTER "/status/";
  sysStr_[SSDataStatusDetector]   = api + ODIN_DATA_ADAPTER "/status/" + pluginName + "/";
  sysStr_[SSDataStatusHDF]        = api + ODIN_DATA_ADAPTER "/status/" PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSDataConfig]           = api + ODIN_DATA_ADAPTER "/config/";
  sysStr_[SSDataConfigDetector]   = api + ODIN_DATA_ADAPTER "/config/" + pluginName + "/";
  sysStr_[SSDataConfigHDF]        = api + ODIN_DATA_ADAPTER "/config/" PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSDataConfigHDFProcess] = api + ODIN_DATA_ADAPTER "/config/" PLUGIN_INDEX_FILE_WRITER
                                    "/process/";
}

std::string OdinRestAPI::sysStr(sys_t sys)
{
  return sysStr_[sys];
}

int OdinRestAPI::connectDetector()
{
  JsonDict stateDict = JsonDict("state", true);
  JsonDict connect = JsonDict("connect", stateDict);
  return put(sysStr(SSDetectorCommand), CONNECT, connect.str());
}

int OdinRestAPI::disconnectDetector()
{
  JsonDict stateDict = JsonDict("state", false);
  JsonDict connect = JsonDict("connect", stateDict);
  return put(sysStr(SSDetectorCommand), CONNECT, connect.str());
}

int OdinRestAPI::startAcquisition()
{
  return put(sysStr(SSDetectorCommand), START_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinRestAPI::stopAcquisition()
{
  return put(sysStr(SSDetectorCommand), STOP_ACQUISITION, "", EMPTY_JSON_STRING);
}

int OdinRestAPI::configureSharedMemoryChannels(std::vector<std::string>& ipAddresses,
                                               std::vector<int> readyPorts,
                                               std::vector<int> releasePorts)
{
  int status = 0;
  for (int index = 0; (size_t) index != ipAddresses.size(); ++index) {
    std::stringstream ready, release, endpoint;
    ready << "tcp://" << ipAddresses[index] << ":" << readyPorts[index];
    release << "tcp://" << ipAddresses[index] << ":" << releasePorts[index];
    endpoint << FR_SETUP << "/" << index;

    std::vector<JsonDict> channelConfig;
    channelConfig.push_back(JsonDict(FR_READY_CNXN, ready.str().c_str()));
    channelConfig.push_back(JsonDict(FR_RELEASE_CNXN, release.str().c_str()));
    JsonDict channelDict = JsonDict(channelConfig);

    status |= put(sysStr(SSDataConfig), endpoint.str(), channelDict.str());
  }
  return status;
}

int OdinRestAPI::loadPlugin(const std::string& modulePath,
                            const std::string& name, const std::string& index,
                            const std::string& library) {
  std::vector<JsonDict> loadConfig;
  std::stringstream fullPath;
  fullPath << modulePath << "/" << ODIN_DATA_LIB_PATH << "/" << library;

  loadConfig.push_back(JsonDict(PLUGIN_NAME, name.c_str()));
  loadConfig.push_back(JsonDict(PLUGIN_INDEX, index.c_str()));
  loadConfig.push_back(JsonDict(PLUGIN_LIBRARY, fullPath.str().c_str()));
  JsonDict loadDict = JsonDict(loadConfig);
  JsonDict config = JsonDict(PLUGIN_LOAD, loadDict);

  return put(sysStr(SSDataConfig), PLUGIN, config.str());
}

int OdinRestAPI::loadProcessPlugin(const std::string& modulePath, const std::string& pluginIndex)
{
  std::stringstream sPluginName;
  sPluginName << pluginIndex << "ProcessPlugin";
  std::string pluginName = sPluginName.str();
  pluginName[0] = toupper(pluginName[0]);
  std::stringstream sLibrary;
  sLibrary << "lib" << pluginName << ".so";

  return loadPlugin(modulePath, pluginName, pluginIndex, sLibrary.str());
}

int OdinRestAPI::loadFileWriterPlugin(const std::string& odinDataPath)
{
  return loadPlugin(odinDataPath, FILE_WRITER_CLASS, PLUGIN_INDEX_FILE_WRITER, FILE_WRITER_LIB);
}

int OdinRestAPI::connectPlugins(const std::string& index, const std::string& connection) {
  std::vector<JsonDict> connectionConfig;
  connectionConfig.push_back(JsonDict(PLUGIN_INDEX, index.c_str()));
  connectionConfig.push_back(JsonDict(PLUGIN_CONNECTION, connection.c_str()));
  JsonDict connectionDict = JsonDict(connectionConfig);
  JsonDict configDict = JsonDict(PLUGIN_CONNECT, connectionDict);

  return put(sysStr(SSDataConfig), PLUGIN, configDict.str());
}

int OdinRestAPI::connectToFrameReceiver(const std::string& index) {

  return connectPlugins(index, PLUGIN_INDEX_FRAME_RECEIVER);
}

int OdinRestAPI::connectToProcessPlugin(const std::string& index) {

  return connectPlugins(index, mDetectorName);
}

int OdinRestAPI::createFile(const std::string& name, const std::string& path) {
  std::vector<JsonDict> fileConfig;
  fileConfig.push_back(JsonDict(FILE_NAME, name.c_str()));
  fileConfig.push_back(JsonDict(FILE_PATH, path.c_str()));
  JsonDict fileDict = JsonDict(fileConfig);
  JsonDict configDict = JsonDict(FILE, fileDict);

  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, configDict.str());
}

int OdinRestAPI::startWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, true);
  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinRestAPI::stopWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, false);
  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinRestAPI::createDataset(const std::string& name, int dataType,
                               std::vector<int>& imageDims, std::vector<int>& chunkDims) {
  std::vector<JsonDict> datasetConfig;
  datasetConfig.push_back(JsonDict(DATASET_CMD, DATASET_CMD_CREATE));
  datasetConfig.push_back(JsonDict(DATASET_NAME, name.c_str()));
  datasetConfig.push_back(JsonDict(DATASET_DATATYPE, dataType));
  datasetConfig.push_back(JsonDict(DATASET_DIMS, imageDims));
  datasetConfig.push_back(JsonDict(DATASET_CHUNKS, chunkDims));
  JsonDict datasetDict = JsonDict(datasetConfig);
  JsonDict configDict = JsonDict(DATASET, datasetDict);

  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, configDict.str());
}

int OdinRestAPI::lookupAccessMode(
        std::string subSystem, rest_access_mode_t &accessMode)
{
    long ssEnum = std::distance(sysStr_, std::find(sysStr_, sysStr_ + SSCount, subSystem));

    switch(ssEnum)
    {
      case SSDetector: case SSDataConfig: case SSDataConfigHDF:
        accessMode = REST_ACC_RW;
        return EXIT_SUCCESS;
      case SSRoot: case SSDetectorStatus:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      case SSDetectorCommand:
        accessMode = REST_ACC_WO;
        default:
          return EXIT_FAILURE;
    }
}

#include "odinDataRestApi.h"

#include <stdexcept>
#include <algorithm>
#include <stdlib.h>

#include "jsonDict.h"
#include "odinDataConfig.h"

// REST Strings
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
#define FILE_PROCESS_RANK           "process/rank"
#define FILE_NAME                   "name"
#define FILE_PATH                   "path"
#define FILE_WRITE                  "write"
#define DATASET                     "dataset"
#define DATASET_DIMS                "dims"
#define DATASET_CHUNKS              "chunks"


const std::string OdinDataRestAPI::FILE_WRITER_PLUGIN = PLUGIN_INDEX_FILE_WRITER;


OdinDataRestAPI::OdinDataRestAPI(const std::string& hostname,
                                 const std::string& pluginName,
                                 int port,
                                 size_t numSockets) :
    OdinRestAPI(hostname, port, numSockets),
    mPluginName(pluginName),
    mProcessPluginIndex("")

{
  const std::string api = "/api/" API_VERSION "/";

  sysStr_[SSDataStatus]           = api + ODIN_DATA_ADAPTER "/status/";
  sysStr_[SSDataStatusDetector]   = api + ODIN_DATA_ADAPTER "/status/" + pluginName + "/";
  sysStr_[SSDataStatusHDF]        = api + ODIN_DATA_ADAPTER "/status/" PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSDataConfig]           = api + ODIN_DATA_ADAPTER "/config/";
  sysStr_[SSDataConfigDetector]   = api + ODIN_DATA_ADAPTER "/config/" + pluginName + "/";
  sysStr_[SSDataConfigHDF]        = api + ODIN_DATA_ADAPTER "/config/" PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSDataConfigHDFProcess] = api + ODIN_DATA_ADAPTER "/config/" PLUGIN_INDEX_FILE_WRITER
                                    "/process/";
  sysStr_[SSDataConfigHDFDataset] = api + ODIN_DATA_ADAPTER "/config/" PLUGIN_INDEX_FILE_WRITER
                                    "/dataset/";
}

int OdinDataRestAPI::configureSharedMemoryChannels(ODConfiguration config)
{
  std::stringstream ready, release, endpoint;
  ready << "tcp://" << config.ipAddress << ":" << config.readyPort;
  release << "tcp://" << config.ipAddress << ":" << config.releasePort;
  endpoint << FR_SETUP << "/" << config.rank;

  std::vector<JsonDict> channelConfig;
  channelConfig.push_back(JsonDict(FR_READY_CNXN, ready.str().c_str()));
  channelConfig.push_back(JsonDict(FR_RELEASE_CNXN, release.str().c_str()));
  JsonDict channelDict = JsonDict(channelConfig);

  return put(sysStr(SSDataConfig), endpoint.str(), channelDict.str());
}

int OdinDataRestAPI::loadPlugin(const std::string& modulePath,
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

int OdinDataRestAPI::loadProcessPlugin(const std::string& modulePath, const std::string& pluginIndex)
{
  std::stringstream sPluginName;
  mProcessPluginIndex = pluginIndex;
  sPluginName << pluginIndex << "ProcessPlugin";
  std::string pluginName = sPluginName.str();
  pluginName[0] = toupper(pluginName[0]);
  std::stringstream sLibrary;
  sLibrary << "lib" << pluginName << ".so";

  return loadPlugin(modulePath, pluginName, pluginIndex, sLibrary.str());
}

int OdinDataRestAPI::loadFileWriterPlugin(const std::string& odinDataPath)
{
  return loadPlugin(odinDataPath, FILE_WRITER_CLASS, PLUGIN_INDEX_FILE_WRITER, FILE_WRITER_LIB);
}

int OdinDataRestAPI::connectPlugins(const std::string& index, const std::string& connection) {
  std::vector<JsonDict> connectionConfig;
  connectionConfig.push_back(JsonDict(PLUGIN_INDEX, index.c_str()));
  connectionConfig.push_back(JsonDict(PLUGIN_CONNECTION, connection.c_str()));
  JsonDict connectionDict = JsonDict(connectionConfig);
  JsonDict configDict = JsonDict(PLUGIN_CONNECT, connectionDict);

  return put(sysStr(SSDataConfig), PLUGIN, configDict.str());
}

int OdinDataRestAPI::connectToFrameReceiver(const std::string& index) {

  return connectPlugins(index, PLUGIN_INDEX_FRAME_RECEIVER);
}

int OdinDataRestAPI::connectToProcessPlugin(const std::string& index) {

  return connectPlugins(index, mProcessPluginIndex);
}

int OdinDataRestAPI::createFile(const std::string& name, const std::string& path) {
  std::vector<JsonDict> fileConfig;
  fileConfig.push_back(JsonDict(FILE_NAME, name.c_str()));
  fileConfig.push_back(JsonDict(FILE_PATH, path.c_str()));
  JsonDict fileDict = JsonDict(fileConfig);
  JsonDict configDict = JsonDict(FILE, fileDict);

  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, configDict.str());
}

int OdinDataRestAPI::startWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, true);
  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinDataRestAPI::stopWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, false);
  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinDataRestAPI::createDataset(const std::string& name) {
  JsonDict configDict = JsonDict(DATASET, name.c_str());

  return put(sysStr(SSDataConfig), PLUGIN_INDEX_FILE_WRITER, configDict.str());
}

int OdinDataRestAPI::setImageDims(const std::string& datasetName, std::vector<int>& imageDims) {
  JsonDict dimsDict = JsonDict(DATASET_DIMS, imageDims);

  return put(sysStr(SSDataConfigHDF), DATASET "/" + datasetName, dimsDict.str());
}

int OdinDataRestAPI::setChunkDims(const std::string& datasetName, std::vector<int>& chunkDims) {
  JsonDict dimsDict = JsonDict(DATASET_CHUNKS, chunkDims);

  return put(sysStr(SSDataConfigHDF), DATASET "/" + datasetName, dimsDict.str());
}

int OdinDataRestAPI::lookupAccessMode(std::string subSystem, rest_access_mode_t& accessMode)
{
    long ssEnum = std::distance(sysStr_, std::find(sysStr_, sysStr_ + SSCount, subSystem));

    switch(ssEnum)
    {
      case SSDataConfig: case SSDataConfigDetector: case SSDataConfigHDF:
      case SSDataConfigHDFProcess: case SSDataConfigHDFDataset:
        accessMode = REST_ACC_RW;
        return EXIT_SUCCESS;
      case SSDataStatus: case SSDataStatusHDF: case SSDataStatusDetector:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      default:
        return OdinRestAPI::lookupAccessMode(subSystem, accessMode);
    }
}

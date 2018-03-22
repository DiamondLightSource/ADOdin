#include "odinDataRestApi.h"

#include <stdexcept>
#include <algorithm>

#include "jsonDict.h"

// REST Strings
#define FRAME_PROCESSOR_ADAPTER     "fp"
#define FRAME_RECEIVER_ADAPTER      "fr"

// OdinData JSON Strings
#define PLUGIN_INDEX_FILE_WRITER    "hdf"
#define FILE                        "file"
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
  sysStr_[SSFPStatus]           = sysStr_[SSAdapterRoot] + FRAME_PROCESSOR_ADAPTER "/status/";
  sysStr_[SSFPStatusDetector]   = sysStr_[SSFPStatus]    + pluginName + "/";
  sysStr_[SSFPStatusHDF]        = sysStr_[SSFPStatus]    + PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSFPConfig]           = sysStr_[SSAdapterRoot] + FRAME_PROCESSOR_ADAPTER "/config/";
  sysStr_[SSFPConfigDetector]   = sysStr_[SSFPConfig]    + pluginName + "/";
  sysStr_[SSFPConfigHDF]        = sysStr_[SSFPConfig]    + PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSFPConfigHDFProcess] = sysStr_[SSFPConfigHDF] + "process/";
  sysStr_[SSFPConfigHDFDataset] = sysStr_[SSFPConfigHDF] + "dataset/";
  sysStr_[SSFRConfig]           = sysStr_[SSAdapterRoot] + FRAME_RECEIVER_ADAPTER "/config/";
  sysStr_[SSFRStatus]           = sysStr_[SSAdapterRoot] + FRAME_RECEIVER_ADAPTER "/status/";
}

int OdinDataRestAPI::createFile(const std::string& name, const std::string& path) {
  std::vector<JsonDict> fileConfig;
  fileConfig.push_back(JsonDict(FILE_NAME, name.c_str()));
  fileConfig.push_back(JsonDict(FILE_PATH, path.c_str()));
  JsonDict fileDict = JsonDict(fileConfig);
  JsonDict configDict = JsonDict(FILE, fileDict);

  return put(sysStr(SSFPConfig), PLUGIN_INDEX_FILE_WRITER, configDict.str());
}

int OdinDataRestAPI::startWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, true);
  return put(sysStr(SSFPConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinDataRestAPI::stopWrite() {
  JsonDict writeDict = JsonDict(FILE_WRITE, false);
  return put(sysStr(SSFPConfig), PLUGIN_INDEX_FILE_WRITER, writeDict.str());
}

int OdinDataRestAPI::setImageDims(const std::string& datasetName, std::vector<int>& imageDims) {
  JsonDict dimsDict = JsonDict(DATASET_DIMS, imageDims);

  return put(sysStr(SSFPConfigHDF), DATASET "/" + datasetName, dimsDict.str());
}

int OdinDataRestAPI::setChunkDims(const std::string& datasetName, std::vector<int>& chunkDims) {
  JsonDict dimsDict = JsonDict(DATASET_CHUNKS, chunkDims);

  return put(sysStr(SSFPConfigHDF), DATASET "/" + datasetName, dimsDict.str());
}

int OdinDataRestAPI::lookupAccessMode(std::string subSystem, rest_access_mode_t& accessMode)
{
    long ssEnum = std::distance(sysStr_, std::find(sysStr_, sysStr_ + SSCount, subSystem));

    switch(ssEnum)
    {
    case SSFRConfig: case SSFPConfig: case SSFPConfigDetector: case SSFPConfigHDF:
      case SSFPConfigHDFProcess: case SSFPConfigHDFDataset:
        accessMode = REST_ACC_RW;
        return EXIT_SUCCESS;
      case SSFPStatus: case SSFPStatusHDF: case SSFPStatusDetector:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      default:
        return OdinRestAPI::lookupAccessMode(subSystem, accessMode);
    }
}

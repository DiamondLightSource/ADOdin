#include "OdinDataRestApi.h"

#include <stdexcept>
#include <algorithm>
#include <frozen.h>

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


std::vector<std::vector<std::string> > parse2DArray (struct json_token *tokens, std::string const& name)
{
  std::vector<std::vector<std::string> > arrayValues;
  struct json_token *t;
  if(name.empty()){
    t = tokens;
  } else {
    t = find_json_token(tokens, name.c_str());
  }
  // We expect to find an array of arrays
  if(t){
    if(t->type == JSON_TYPE_ARRAY){
      int i = 1;
      while (i <= t->num_desc){
        std::vector<std::string> x_vals;
        struct json_token *array = t+i;
        if(array->type == JSON_TYPE_ARRAY){
          for(int x = 1; x <= array->num_desc; ++x){
            std::string entry((array+x)->ptr, (array+x)->len);
            x_vals.push_back(entry);
            i++;
          }
        }
        i++;
        arrayValues.push_back(x_vals);
      }
    }
  }
  return arrayValues;
}

OdinDataRestAPI::OdinDataRestAPI(const std::string& hostname,
                                 const std::string& pluginName,
                                 int port,
                                 size_t numSockets) :
    OdinRestAPI(hostname, port, numSockets),
    mPluginName(pluginName),
    mProcessPluginIndex("")

{
  sysStr_[SSFP]                 = sysStr_[SSAdapterRoot] + FRAME_PROCESSOR_ADAPTER + "/";
  sysStr_[SSFPStatus]           = sysStr_[SSFP]          + "status/";
  sysStr_[SSFPConfig]           = sysStr_[SSFP]          + "config/";
  sysStr_[SSFPConfigDetector]   = sysStr_[SSFPConfig]    + pluginName + "/";
  sysStr_[SSFPStatusDetector]   = sysStr_[SSFPStatus]    + pluginName + "/";
  sysStr_[SSFPStatusHDF]        = sysStr_[SSFPStatus]    + PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSFPConfigHDF]        = sysStr_[SSFPConfig]    + PLUGIN_INDEX_FILE_WRITER "/";
  sysStr_[SSFPConfigHDFProcess] = sysStr_[SSFPConfigHDF] + "process/";
  sysStr_[SSFPConfigHDFDataset] = sysStr_[SSFPConfigHDF] + "dataset/";
  sysStr_[SSFR]                 = sysStr_[SSAdapterRoot] + FRAME_RECEIVER_ADAPTER "/";
  sysStr_[SSFRConfig]           = sysStr_[SSFR]          + "config/";
  sysStr_[SSFRStatus]           = sysStr_[SSFR]          + "status/";
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

std::string OdinDataRestAPI::readError(int address, int error_index) {
  // Parse JSON
  struct json_token tokens[256];
  std::string error = "";
  std::string buffer;

  get(sysStr(SSFPStatus), "client_error", buffer, 1);
  parse_json(buffer.c_str(), buffer.size(), tokens, 256);
  std::vector<std::vector<std::string> > valueArray = parse2DArray(tokens, PARAM_VALUE);

  if ((int) valueArray.size() > address) {
    std::vector<std::string> singleArray = valueArray[address];
    if ((int) singleArray.size() > error_index) {
      error = singleArray[error_index];
    }
  }
  return error;
}

int OdinDataRestAPI::lookupAccessMode(std::string subSystem, rest_access_mode_t& accessMode)
{
    long ssEnum = std::distance(sysStr_, std::find(sysStr_, sysStr_ + SSCount, subSystem));

    switch(ssEnum)
    {
    case SSFRConfig: case SSFPConfig: case SSFPConfigDetector: case SSFPConfigHDF:
      case SSFPConfigHDFProcess: case SSFPConfigHDFDataset: case SSAdapterRoot:
        accessMode = REST_ACC_RW;
        return EXIT_SUCCESS;
      case SSFPStatus: case SSFPStatusHDF: case SSFPStatusDetector:
        accessMode = REST_ACC_RO;
        return EXIT_SUCCESS;
      default:
        return OdinRestAPI::lookupAccessMode(subSystem, accessMode);
    }
}

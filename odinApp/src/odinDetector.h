#ifndef EIGER_DETECTOR_H
#define EIGER_DETECTOR_H

#include "ADDriver.h"
#include "odinRestApi.h"

#define OdinRestAPIVersion             "ODIN_REST_API_VERSION"
#define OdinConnected                  "ODIN_CONNECTED"
#define OdinNumPending                 "ODIN_NUM_PENDING"
#define OdinNumProcesses               "ODIN_NUM_PROCESSES"
#define OdinHDF5FilePath               "ODIN_HDF5_FILE_PATH"
#define OdinHDF5FilePathExists         "ODIN_HDF5_FILE_PATH_EXISTS"
#define OdinHDF5FileName               "ODIN_HDF5_FILE_NAME"
#define OdinHDF5FileTemplate           "ODIN_HDF5_FILE_TEMPLATE"
#define OdinHDF5NumCapture             "ODIN_HDF5_FILE_NAME"
#define OdinHDF5ImageWidth             "ODIN_HDF5_IMAGE_WIDTH"
#define OdinHDF5ImageHeight            "ODIN_HDF5_IMAGE_HEIGHT"
#define OdinHDF5ChunkWidth             "ODIN_HDF5_CHUNK_WIDTH"
#define OdinHDF5ChunkHeight            "ODIN_HDF5_CHUNK_HEIGHT"
#define OdinHDF5ChunkDepth             "ODIN_HDF5_CHUNK_DEPTH"
#define OdinHDF5ChunkBoundaryAlign     "ODIN_HDF5_CHUNK_BOUNDARY_ALIGN"
#define OdinHDF5ChunkBoundaryThreshold "ODIN_HDF5_CHUNK_BOUNDARY_THRESHOLD"
#define OdinHDF5NumFramesPersh         "ODIN_HDF5_NUM_FRAMES_PER_FLUSH"
#define OdinHDF5Compression            "ODIN_HDF5_COMPRESSION"
#define OdinHDF5FillValue              "ODIN_HDF5_FILL_VALUE"

class OdinDetector : public ADDriver
{
 public:
  OdinDetector(const char * portName, const char * serverHostname,
               const char * detectorName, int maxBuffers,
               size_t maxMemory, int priority, int stackSize);
  int createDetectorParams();
  int createOdinDataParams();

  // These are the methods that we override from ADDriver
  virtual asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);
  virtual asynStatus writeFloat64(asynUser *pasynUser, epicsFloat64 value);
  virtual asynStatus writeOctet(
      asynUser *pasynUser, const char *value,
      size_t nChars, size_t *nActual);
  asynStatus callParamCallbacks();
  void report(FILE *fp, int details);
  virtual asynStatus drvUserCreate(
      asynUser *pasynUser, const char *drvInfo,
      const char **pptypeName, size_t *psize);

  // EPICS API
  asynStatus acquireStart(const std::string &fileName, const std::string &filePath,
                          const std::string &datasetName, int dataType);
  asynStatus acquireStop();

  // IOC Init Methods
  static void configureOdinData(const char * libraryPath, const char * ipAddress,
                                int readyPort, int releasePort, int metaPort);
  static std::string mOdinDataLibraryPath;
  static std::string mIPAddress;
  static int mReadyPort;
  static int mReleasePort;
  static int mMetaPort;
  static void configureDetector(const char * detectorName, const char * libraryPath);
  static std::string mProcessPluginName;
  static std::string mDetectorLibraryPath;

 private:
  char mHostname[512];
  OdinRestAPI mAPI;
  RestParamSet mParams;

  int mFirstParam;

  RestParam * createRESTParam(const std::string& asynName, rest_param_type_t restType,
                              sys_t subSystem, const std::string& name, bool arrayValue = false);
  RestParam * mAPIVersion;
  RestParam * mConnected;
  RestParam * mNumPending;
  RestParam * mProcesses;
  RestParam * mFilePath;
  RestParam * mFileName;

  // Internal PVs
  int mImageHeight;
  int mImageWidth;
  int mChunkDepth;
  int mChunkHeight;
  int mChunkWidth;

  asynStatus getStatus();
  std::vector<int> getImageDimensions();
  std::vector<int> getChunkDimensions();

};

#endif

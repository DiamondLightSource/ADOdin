#ifndef EIGER_DETECTOR_H
#define EIGER_DETECTOR_H

#include "OdinClient.h"
#include "odinDataConfig.h"
#include "odinDataRestApi.h"

// Odin Server
#define OdinRestAPIVersion             "ODIN_REST_API_VERSION"
// Detector
#define OdinDetectorConnected          "ODIN_DETECTOR_CONNECTED"
// OdinData
#define OdinNumProcesses               "ODIN_NUM_PROCESSES"
#define OdinProcessRank                "ODIN_PROCESS_RANK"
#define OdinProcessConnected           "ODIN_PROCESS_CONNECTED"
#define OdinProcessInitialised         "ODIN_PROCESS_INITIALISED"
// -- HDF5
#define OdinHDF5BlockSize              "ODIN_HDF5_BLOCK_SIZE"
#define OdinHDF5BlocksPerFile          "ODIN_HDF5_BLOCKS_PER_FILE"
#define OdinHDF5EarliestVersion        "ODIN_HDF5_EARLIEST_VERSION"
#define OdinHDF5MasterDataset          "ODIN_HDF5_MASTER_DATASET"
#define OdinHDF5OffsetAdjustment       "ODIN_HDF5_OFFSET_ADJUSTMENT"
#define OdinHDF5AcquisitionID          "ODIN_HDF5_ACQUISITION_ID"
#define OdinHDF5CloseFileTimeout       "ODIN_HDF5_CLOSE_FILE_TIMEOUT"
#define OdinHDF5StartCloseTimeout      "ODIN_HDF5_START_CLOSE_TIMEOUT"
#define OdinHDF5FilePath               "ODIN_HDF5_FILE_PATH"
#define OdinHDF5FilePathExists         "ODIN_HDF5_FILE_PATH_EXISTS"
#define OdinHDF5FileName               "ODIN_HDF5_FILE_NAME"
#define OdinHDF5FileTemplate           "ODIN_HDF5_FILE_TEMPLATE"
#define OdinHDF5FullFileName           "ODIN_HDF5_FULL_FILE_NAME"
#define OdinHDF5NumCapture             "ODIN_HDF5_NUM_CAPTURE"
#define OdinHDF5NumCaptured            "ODIN_HDF5_NUM_CAPTURED"
#define OdinHDF5NumExpected            "ODIN_HDF5_NUM_EXPECTED"
#define OdinHDF5NumCapturedSum         "ODIN_HDF5_NUM_CAPTURED_SUM"
#define OdinHDF5Write                  "ODIN_HDF5_WRITE"
#define OdinHDF5Writing                "ODIN_HDF5_WRITING"
#define OdinHDF5WritingAny             "ODIN_HDF5_WRITING_ANY"
#define OdinHDF5ImageWidth             "ODIN_HDF5_IMAGE_WIDTH"
#define OdinHDF5ImageHeight            "ODIN_HDF5_IMAGE_HEIGHT"
#define OdinHDF5ChunkWidth             "ODIN_HDF5_CHUNK_WIDTH"
#define OdinHDF5ChunkHeight            "ODIN_HDF5_CHUNK_HEIGHT"
#define OdinHDF5ChunkDepth             "ODIN_HDF5_CHUNK_DEPTH"
#define OdinHDF5ChunkBoundaryAlignment "ODIN_HDF5_CHUNK_BOUNDARY_ALIGNMENT"
#define OdinHDF5ChunkBoundaryThreshold "ODIN_HDF5_CHUNK_BOUNDARY_THRESHOLD"
#define OdinHDF5NumFramesPerFlush      "ODIN_HDF5_NUM_FRAMES_PER_FLUSH"
#define OdinHDF5Compression            "ODIN_HDF5_COMPRESSION"
#define OdinHDF5FillValue              "ODIN_HDF5_FILL_VALUE"

class OdinDataDriver : public OdinClient
{
 public:
  OdinDataDriver(const char * portName, const char * serverHostname, int odinServerPort,
                 const char * datasetName, const char * fileWriterLibraryPath,
                 const char * detectorName, const char * processPluginLibraryPath,
                 int maxBuffers, size_t maxMemory, int priority, int stackSize);

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
  static void configureOdinDataProcess(const char * ipAddress, int readyPort, int releasePort,
                                       int metaPort);
  static std::vector<ODConfiguration> mODConfig;
  static void configureOdinData(const char * odinDataLibraryPath,
                                const char * detectorName, const char * libraryPath,
                                const char * datasetName);
  static std::string mDatasetName;
  static std::string mFileWriterLibraryPath;
  static std::string mProcessPluginName;
  static std::string mProcessPluginLibraryPath;
  static size_t mODCount;

 private:
  char mHostname[512];
  OdinDataRestAPI mAPI;

  int initialise(int index);
  int initialiseAll();
  std::vector<int> mInitialised;
//  int createDetectorParams();
  int createOdinDataParams();
  bool mOdinDataParamsCreated;

  RestParam * createODRESTParam(const std::string &asynName, rest_param_type_t restType,
                                sys_t subSystem, const std::string &name);

  int mFirstParam;

  RestParam * mAPIVersion;

  RestParam * mConnected;
  RestParam * mNumImages;

  RestParam * mProcesses;
  RestParam * mFilePath;
  RestParam * mFileName;
  RestParam * mBlockSize;
  RestParam * mBlocksPerFile;
  RestParam * mEarliestVersion;
  RestParam * mMasterDataset;
  RestParam * mOffsetAdjustment;
  RestParam * mAcquisitionID;
  RestParam * mCloseFileTimeout;
  RestParam * mStartCloseTimeout;
  RestParam * mNumCapture;
  RestParam * mCapture;
  RestParam * mChunkBoundaryAlignment;
  RestParam * mChunkBoundaryThreshold;
  RestParam * mCompression;
  RestParam * mDataType;

  RestParam * mProcessConnected;
  RestParam * mProcessRank;
  RestParam * mWriting;
  RestParam * mFullFileName;
  RestParam * mNumCaptured;
  RestParam * mNumExpected;

  RestParam * mAcqComplete;

  // Internal PVs
  int mImageHeight;
  int mImageWidth;
  int mChunkDepth;
  int mChunkHeight;
  int mChunkWidth;

  int mProcessInitialised;
  int mNumCapturedSum;
  int mWritingAny;
  int mFileTemplate;

  asynStatus getStatus();
  int configureImageDims();
  int configureChunkDims();

};

#endif

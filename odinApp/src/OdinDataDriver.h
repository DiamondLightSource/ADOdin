#ifndef ODIN_DATA_DRIVER_H
#define ODIN_DATA_DRIVER_H

#include "OdinClient.h"
#include "OdinDataConfig.h"
#include "OdinDataRestApi.h"

// Odin Server
#define OdinRestAPIVersion             "ODIN_REST_API_VERSION"
// OdinData
#define OdinProcessRank                "ODIN_PROCESS_RANK"
#define OdinFPCount                    "ODIN_FP_COUNT"
#define OdinFRCount                    "ODIN_FR_COUNT"
#define OdinFRProcessConnected         "ODIN_FR_PROCESS_CONNECTED"
#define OdinFPProcessConnected         "ODIN_FP_PROCESS_CONNECTED"
#define OdinFPErrorMessage             "ODIN_FP_ERROR_MESSAGE"
#define OdinFPErrorState               "ODIN_FP_ERROR_STATE"
#define OdinFPClearErrors              "ODIN_FP_CLEAR_ERRORS"
#define OdinFRFramesReceived           "ODIN_FR_FRAMES_RECEIVED"
#define OdinFRFramesDropped            "ODIN_FR_FRAMES_DROPPED"
#define OdinFRFramesTimedOut           "ODIN_FR_FRAMES_TIMEDOUT"
#define OdinFRFramesReleased           "ODIN_FR_FRAMES_RELEASED"
// Buffers
#define OdinFRFreeBuffers              "ODIN_FR_FREE_BUFFERS"
// -- HDF5
#define OdinHDF5BlockSize              "ODIN_HDF5_BLOCK_SIZE"
#define OdinHDF5BlocksPerFile          "ODIN_HDF5_BLOCKS_PER_FILE"
#define OdinHDF5EarliestVersion        "ODIN_HDF5_EARLIEST_VERSION"
#define OdinHDF5MasterDataset          "ODIN_HDF5_MASTER_DATASET"
#define OdinHDF5OffsetAdjustment       "ODIN_HDF5_OFFSET_ADJUSTMENT"
#define OdinHDF5CloseFileTimeout       "ODIN_HDF5_CLOSE_FILE_TIMEOUT"
#define OdinHDF5StartCloseTimeout      "ODIN_HDF5_START_CLOSE_TIMEOUT"
#define OdinHDF5TimeoutActive          "ODIN_HDF5_TIMEOUT_ACTIVE"
#define OdinHDF5TimeoutActiveAny       "ODIN_HDF5_TIMEOUT_ACTIVE_ANY"
#define OdinHDF5FileExtension          "ODIN_HDF5_FILE_EXTENSION"
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
                 const char * datasetName, const char * detectorName,
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

  int createParams();

  RestParam * createODRESTParam(const std::string &asynName, rest_param_type_t restType,
                                sys_t subSystem, const std::string &name);

  RestParam * mAPIVersion;
  RestParam * mConnected;
  RestParam * mNumImages;
  RestParam * mFileExtension;
  RestParam * mBlockSize;
  RestParam * mBlocksPerFile;
  RestParam * mEarliestVersion;
  RestParam * mMasterDataset;
  RestParam * mOffsetAdjustment;
  RestParam * mCloseFileTimeout;
  RestParam * mStartCloseTimeout;
  RestParam * mNumCapture;
  RestParam * mCapture;
  RestParam * mChunkBoundaryAlignment;
  RestParam * mChunkBoundaryThreshold;
  RestParam * mCompression;
  RestParam * mDataType;
  RestParam * mFreeBuffers;
  RestParam * mFramesReceived;
  RestParam * mFramesDropped;
  RestParam * mFramesTimedOut;
  RestParam * mFramesReleased;

  RestParam * mFPProcessConnected;
  RestParam * mFRProcessConnected;
  RestParam * mFPCount;
  RestParam * mFRCount;
  int mFPErrorMessage;
  RestParam * mFPClearErrors;
  RestParam * mProcessRank;
  RestParam * mWriting;
  RestParam * mTimeoutActive;
  RestParam * mFullFileName;
  RestParam * mNumCaptured;
  RestParam * mNumExpected;

  // Internal PVs
  int mFPErrorState;
  int mNumCapturedSum;
  int mWritingAny;
  int mTimeoutActiveAny;
  int mImageHeight;
  int mImageWidth;
  int mChunkDepth;
  int mChunkHeight;
  int mChunkWidth;

  asynStatus getStatus();
  int configureImageDims();
  int configureChunkDims();

};

#endif

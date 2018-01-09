#ifndef EIGER_DETECTOR_H
#define EIGER_DETECTOR_H

#include "ADDriver.h"
#include "odinRestApi.h"

#define OdinRestAPIVersion "ODIN_REST_API_VERSION"
#define OdinConnected      "ODIN_CONNECTED"
#define OdinNumPending     "ODIN_NUM_PENDING"

class OdinDetector : public ADDriver
{
 public:
  OdinDetector(const char * portName, const char * serverHostname,
               int maxBuffers, size_t maxMemory, int priority, int stackSize);
  int createDetectorParams();
  int createOdinDataParams();

  // These are the methods that we override from ADDriver
  virtual asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);
  virtual asynStatus writeFloat64(asynUser *pasynUser, epicsFloat64 value);
  virtual asynStatus writeOctet(
      asynUser *pasynUser, const char *value,
      size_t nChars, size_t *nActual);
  void report(FILE *fp, int details);
  virtual asynStatus drvUserCreate(
      asynUser *pasynUser, const char *drvInfo,
      const char **pptypeName, size_t *psize);

  // EPICS API
  asynStatus acquireStart(const std::string &fileName, const std::string &filePath,
                          const std::string &datasetName, int dataType,
                          std::vector<int>& imageDims, std::vector<int>& chunkDims);
  asynStatus acquireStop();

  // IOC Init Methods
  static void configureOdinData(const char * libraryPath, const char * ipAddress,
                                int readyPort, int releasePort, int metaPort);
  static std::string mOdinDataLibraryPath;
  static std::string mIPAddress;
  static int mReadyPort;
  static int mReleasePort;
  static int mMetaPort;
  static void configureDetector(const char * detectorName, const char * libraryPath,
                                int detectorHeight, int detectorWidth);
  static std::string mDetectorName;
  static std::string mDetectorLibraryPath;
  static std::vector<int> mImageDims;
  static std::vector<int> mChunkDims;

 private:
  char mHostname[512];
  OdinRestAPI mAPI;
  RestParamSet mParams;

  int mFirstParam;

  RestParam * createRESTParam(
      std::string const & asynName, rest_param_type_t restType,
      sys_t subSystem, std::string const & name);
  RestParam * mAPIVersion;
  RestParam * mConnected;
  RestParam * mNumPending;
  RestParam * mFilePath;
  RestParam * mFileName;

  asynStatus getStatus();

};

#endif

#ifndef EIGER_DETECTOR_H
#define EIGER_DETECTOR_H

#include "ADDriver.h"
#include "restParam.h"

#include "odinRestApi.h"

#define RestAPIVersion "REST_API_VERSION"
#define Connected      "CONNECTED"
#define NumPending     "NUM_PENDING"

class OdinDetector : public ADDriver
{
 public:
  OdinDetector(
      const char *portName, const char *serverHostname,
      int maxBuffers, size_t maxMemory, int priority, int stackSize);

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

  static void configureOdinData(const char * libraryPath);
  static std::string mOdinDataLibraryPath;
  static void configureDetector(const char * detectorName, const char * libraryPath);
  static std::string mDetectorName;
  static std::string mDetectorLibraryPath;

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

  asynStatus getStatus();

};

#endif

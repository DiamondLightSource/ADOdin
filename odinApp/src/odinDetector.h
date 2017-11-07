#ifndef EIGER_DETECTOR_H
#define EIGER_DETECTOR_H

#include "ADDriver.h"
#include "restParam.h"

class odinDetector : public ADDriver
{
public:
  odinDetector(
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
};

#endif

/*
 * OdinClient.h
 *
 *  Created on: 21 Feb 2018
 *      Author: gnx91527
 */

#ifndef ODIN_CLIENT_H
#define ODIN_CLIENT_H

#include "ADDriver.h"
#include "OdinDataConfig.h"
#include "OdinRestApi.h"

// Odin Server
#define OdinRestAPIVersion             "ODIN_REST_API_VERSION"

class OdinClient : public ADDriver
{
public:
  OdinClient(const char * portName,
             const char * serverHostname,
             int odinServerPort,
             const char * detectorName,
             int maxBuffers,
             size_t maxMemory,
             int priority,
             int stackSize);

  void registerAPI(OdinRestAPI *api);

  virtual ~OdinClient();

protected:
  RestParam * createRESTParam(const std::string &asynName, rest_param_type_t restType,
                              sys_t subSystem, const std::string &name, size_t arraySize = 0);

  asynStatus dynamicParam(asynUser *pasynUser,
                          const char *drvInfo,
                          const char **pptypeName,
                          size_t *psize,
                          sys_t subsystem);

  int fetchParams();
  int pushParams();
  RestParam *getParamByIndex(int index);

  int mFirstParam;
  RestParam * mAPIVersion;
  RestParam * mErrorMessage;

private:
  char mHostname[512];
  OdinRestAPI *mAPI;
  RestParamSet *mParams;

};

#endif /* ODINAPP_SRC_ODINCLIENT_H_ */

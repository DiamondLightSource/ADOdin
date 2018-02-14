#ifndef ODIN_DATA_CONFIG_H
#define ODIN_DATA_CONFIG_H


struct ODConfiguration {
  size_t rank;
  std::string ipAddress;
  int readyPort;
  int releasePort;
  int metaPort;
  ODConfiguration(size_t rank, std::string ipAddress, int readyPort, int releasePort, int metaPort):
      rank(rank), ipAddress(ipAddress), readyPort(readyPort), releasePort(releasePort),
      metaPort(metaPort){}
};

#endif

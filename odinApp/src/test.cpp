#include <iostream>
#include <string>

#include "odinDetector.h"

int main()
{
  OdinDetector * detector = new OdinDetector("EXC.CAM", "0.0.0.0", 0, 0, 0, 0);

  std::cout << "Status:\n\n" << detector->statusUpdate();
}

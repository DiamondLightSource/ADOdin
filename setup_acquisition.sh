#!/bin/bash

caput -S ODINDETECTOR:CAM:FilePath /tmp
caput -S ODINDETECTOR:CAM:AcquisitionID image_001
caput -S ODINDETECTOR:CAM:FileTemplate %s.hdf5
caput ODINDETECTOR:CAM:NumCapture 10
caput ODINDETECTOR:CAM:ImageHeight 256
caput ODINDETECTOR:CAM:NumRowChunks 256
caput ODINDETECTOR:CAM:FrameOffset 0
caput ODINDETECTOR:CAM:CloseFileTimeout 0
caput ODINDETECTOR:CAM:BlockSize 1
caput ODINDETECTOR:CAM:BlocksPerFile 0

caput ODINDETECTOR:CAM:Capture 1

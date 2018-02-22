#!/bin/bash

caput -S ODINDETECTOR:OD:FilePath /tmp
caput -S ODINDETECTOR:OD:AcquisitionID image_001
caput -S ODINDETECTOR:OD:FileTemplate %s.hdf5
caput ODINDETECTOR:OD:NumCapture 10
caput ODINDETECTOR:OD:ImageHeight 256
caput ODINDETECTOR:OD:NumRowChunks 256
caput ODINDETECTOR:OD:FrameOffset 0
caput ODINDETECTOR:OD:CloseFileTimeout 0
caput ODINDETECTOR:OD:BlockSize 1
caput ODINDETECTOR:OD:BlocksPerFile 0

caput ODINDETECTOR:OD:Capture 1

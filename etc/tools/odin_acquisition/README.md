# Odin detector test acquisitions

odin_acquisition is a package containing scripts for running test odin detector acquisitions.

The test acquisition scripts are intended as tools to verify an odin detector deployment is functioning correctly at the basic level.

They are generalised for use across multiple beamlines and therefore do not test any beamline specific functionality or modes of operation.

However, the scripts may be used as [templates for more advanced debugging.](#using-as-a-template-for-further-debugging)

## Installation

The scripts can be used with python 3 available at DLS as dls-python3.

### Python 3 installation

To install, first create a virtual environment, then activate the environment and install the package.

At DLS:

```
dls-python3 -m venv /scratch/<fedID>/virtualenvs/test_detector_venv
source /scratch/<fedID>/virtualenvs/test_detector_venv/bin/activate
pip3 install <path-to-ADOdin>/ADOdin/etc/tools/odin_acquisition
```

## Eiger

### Usage

With virtual environment active:

```
==> eiger_acquisition -h
usage: eiger_acquisition [-h] [--log_file_name LOG_FILE_NAME]
                           [--log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                           pv_stem parameter_list [parameter_list ...]
                           filepath filename log_file_directory

Run one or more test eiger + odin acquisitions

positional arguments:
  pv_stem               The Eiger pv stem e.g. BL04I-EA-EIGER-01
  parameter_list        Comma separated pairs of acquistion period and number
                        of images. Separate pairs with whitespace e.g.
                        0.005,100 0.02,10
  filepath              Path to data directory
  filename              Data filename stem (will be appended with acquisition
                        num if multiple acquisitions)
  log_file_directory    Directory to write log file

optional arguments:
  -h, --help            show this help message and exit
  --log_file_name LOG_FILE_NAME
                        Filename of log file
  --log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level
```

For example:
```
eiger_acquisition BL***-EA-EIGER-** 0.005,3600 0.02,600 <data_filepath> <data_filename_stem> /home/fedID
```
This will run two acquisitions. The first has acquire time 0.005 s and collects 3600 frames. The second has acquire time 0.02 s and collects 600 frames. The data files for both acquisitions will be written to <data_filepath>. The log file for the test acquisition is written to /home/fedID/eiger_test.log.


### Extending for debugging

#### Running a series of acquisitions

Rather than running from the command line, a series of acquisitions can be run by creating an `EigerTestDetector` instance and calling `prepare_and_run_acquisition()` once for each acquisition as in the example below. This allows many acquisitions to be run sequentially and allows custom filename and path for each acquisition.

```python
import logging
from pathlib import Path

from odin_acquisition import EigerTestDetector


def main():

    # set the path to the log file
    log_filepath = Path("/home/fedID/<>.log")
    log_level = logging.DEBUG

    # set
    pv_stem = "BL**-EA-EIGER-**"
    num_acquisitions = 100
    acquire_period = 0.05  # seconds
    num_frames = 2600
    filepath = Path("...")  # where data files are written to
    filename_stem = "eiger_test"  # stem of data file name

    # Setup logging
    logging.basicConfig(
        filename=log_filepath,
        level=log_level,
        format="%(asctime)s.%(msecs)03d:%(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # create test detector instance
    detector = EigerTestDetector(pv_stem)

    # run multiple acquisitions
    for id in range(num_acquisitions):
        # Note odin requires different file names for sequential acquisitions
        filename = f"{filename_stem}_{id}"
        detector.prepare_and_run_acquisition(
            filename, filepath, acquire_period, num_frames
        )


if __name__ == "__main__":
    main()
```

#### Using as a template for further debugging

This script covers a very simple use case but can also be used as a template for more advanced debugging by taking a copy of the code and modifying, for example, the PV settings.

Most eiger PV settings can be added or modified here
```python
    def put_eiger_params(self, acquire_period, num_images):
        ...
```

And odin PV settings can be added or modified here
```python
    def put_odin_params(self, file_name, file_path):
        ...
```

import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from time import gmtime, strftime, struct_time
from typing import List

import h5py as h5
import matplotlib.pyplot as plt
import numpy as np
from progress.bar import Bar

META_SUFFIX = "*_meta.h5"
WRITE_DURATION = "write_duration"
FLUSH_DURATION = "flush_duration"
CREATE_DURATION = "create_duration"
CLOSE_DURATION = "close_duration"
ISO_FORMAT_WTIMEZONE = "%Y-%m-%dT%H:%M:%S (%z)"
WARNING_DURATION = 500000  # 0.5 seconds


def files_between(files: List[Path], start: str = None, end: str = None) -> List[Path]:
    """Return files last modified between start and end"""
    if start is not None:
        start_tuple = datetime.fromisoformat(start).timetuple()
        start_idx = file_newer_than(files, start_tuple)
        files = files[start_idx:]

    if end is not None:
        end_tuple = datetime.fromisoformat(end).timetuple()
        end_idx = file_newer_than(files, end_tuple)
        files = files[:end_idx]

    return files


def file_newer_than(files: List[Path], target: struct_time) -> int:
    """Return the index of the first file in the list last modified after target"""
    target_idx = 0
    for idx in range(len(files)):
        if gmtime(os.path.getmtime(files[idx])) > target:
            target_idx = idx
            break

    return target_idx


def find_meta_files(root: Path, recursive: bool = False):
    if recursive:
        return root.rglob(META_SUFFIX)
    else:
        return root.glob(META_SUFFIX)


def iso_time_of_file(file: Path):
    return strftime(ISO_FORMAT_WTIMEZONE, gmtime(os.path.getmtime(file)))


def main():
    parser = ArgumentParser("Find odin meta files and plot metrics")
    parser.add_argument("directories", nargs="+", type=Path, help="Directory tree to search")
    parser.add_argument("--start", default=None, help="Start timestamp")
    parser.add_argument("--end", default=None, help="End timestamp")
    parser.add_argument(
        "--range",
        default=False,
        action="store_true",
        help="Print time range of files found",
    )
    parser.add_argument(
        "-r", "--recursive", default=False, action="store_true", help="Recursive glob"
    )
    args = parser.parse_args()

    dirs = "\n".join([f"  - {str(path)}" for path in args.directories])
    print(f"Finding files matching {META_SUFFIX} in \n{dirs}")
    h5_paths = []
    for root in args.directories:
        for path in find_meta_files(root, args.recursive):
            h5_paths.append(path)
    h5_paths.sort(key=os.path.getmtime)

    if not h5_paths:
        print("No files found")
        exit(1)

    if True:
        start = iso_time_of_file(h5_paths[0])
        end = iso_time_of_file(h5_paths[-1])
        print(f"Range: {start} - {end}")
        #exit(0)

    print(f"Filtering to files between {args.start} and {args.end}")
    h5_paths = files_between(h5_paths, args.start, args.end)

    if not h5_paths:
        print("No files matching range")
        exit(1)

    write_durations = np.array([])
    flush_durations = np.array([])
    create_durations = np.array([])
    close_durations = np.array([])
    bar = Bar(
        "Reading files...",
        suffix="%(index)d / %(max)d [ETA: %(eta)ds]",
        max=len(h5_paths),
    )
    for h5_path in h5_paths:
        try:
            with h5.File(h5_path, "r") as h5_file:
                _write_durations = h5_file[WRITE_DURATION]
                _flush_durations = h5_file[FLUSH_DURATION]
                _create_durations = h5_file[CREATE_DURATION]
                _close_durations = h5_file[CLOSE_DURATION]

                if max(np.append(_write_durations, _flush_durations)) > WARNING_DURATION:
                    print(f" - {h5_path} was slow ({iso_time_of_file(h5_path)})")

                write_durations = np.append(write_durations, _write_durations)
                flush_durations = np.append(flush_durations, _flush_durations)
                create_durations = np.append(create_durations, _create_durations)
                close_durations = np.append(close_durations, _close_durations)
        except Exception:
            print(f"Ignoring {h5_path}")
            # Probably still open for writing
            pass
        bar.next()
    bar.finish()

    print("Plotting")

    _, ax = plt.subplots(2)
    ax[0].set_title("H5 Call Durations")
    ax[1].set_xlabel("Frame Index")

    ax[0].set_ylabel("Write Duration (us)", color="tab:blue")
    ax[0].set_ylim(0, write_durations.max() + flush_durations.max())
    ax[0].plot(write_durations, color="tab:blue", linewidth=0.1)

    ax2 = ax[0].twinx()
    ax2.set_ylabel("Flush Duration (us)", color="tab:red")
    ax2.set_ylim(write_durations.max() + flush_durations.max(), 0)
    ax2.plot(flush_durations, color="tab:red", linewidth=0.1)

    ax[1].set_ylabel("Create Duration (us)", color="tab:blue")
    ax[1].set_ylim(0, create_durations.max() + close_durations.max())
    ax[1].plot(create_durations, color="tab:blue", linewidth=0.1)

    ax2 = ax[1].twinx()
    ax2.set_ylabel("Close Duration (us)", color="tab:red")
    ax2.set_ylim(create_durations.max() + close_durations.max(), 0)
    ax2.plot(close_durations, color="tab:red", linewidth=0.1)

    plt.show()


if __name__ == "__main__":
    sys.exit(main())

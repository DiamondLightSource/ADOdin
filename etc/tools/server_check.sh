#!/bin/bash
# Checks the local machine for odin-data processing setup. Checks for GPFS mount and for shared memory setup

# Check RHEL version
rh="$(cat /etc/redhat-release)"
echo "  Redhat version:" $rh

# Check GPFS is mounted
gpfs="$(mount | grep gpfs | wc -l)"
if (( $gpfs > 0 )); then
  echo "  GPFS Mount: GPFS mounted ("$gpfs" counts)"
else
  echo -e "\e[31m  GPFS Mount: GPFS not mounted\e[0m"
fi

# Check shared memory configuration
num_shm="$(cat /etc/fstab | grep tmpfs | wc -l)"
if (( $num_shm > 0 )); then
  shm="$(cat /etc/fstab | grep tmpfs | grep -o size=[0-9]*%)"
  echo "  Shared Memory: Shared Memory usage percent set:" $shm

  shm_perc="$(cat /etc/fstab | grep tmpfs | grep -o size=[0-9]*% | grep -o '[0-9]*')"

  # Check shared memory configuration has been applied
  total_mem="$(free | grep Mem | awk '{print $2}')"
  echo "    Total memory on system:" $total_mem

  shm_act="$(cat /proc/mounts | grep dev/shm | grep -o size=[0-9]*k | grep -o '[0-9]*')"
  echo "    Actual shared memory that can be used:" $shm_act

  perc_act=$(($((shm_act * 100)) / $((total_mem))))

  if (( $perc_act >= $shm_perc )); then
    echo "    Actual shared memory that can be used is at or above requested:" $perc_act ">=" $shm_perc
  else
    echo -e " \e[31m   Actual shared memory that can be used is less than requested:" $perc_act "<" $shm_perc "\e[0m"
  fi

else
  echo -e "\e[31m  Shared Memory: Shared memory usage percent not set\e[0m"
fi


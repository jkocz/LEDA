#!/usr/bin/env bash
for ii in `seq 1 11`; do
	if [ ! -d /longterm/zfs_longterm/ledaovro$ii ]; then
		mkdir  /longterm/zfs_longterm/ledaovro$ii
		mkdir /longterm/zfs_longterm/ledaovro$ii/data1
		mkdir /longterm/zfs_longterm/ledaovro$ii/data1/one
		mkdir /longterm/zfs_longterm/ledaovro$ii/data1/two
		mkdir /longterm/zfs_longterm/ledaovro$ii/data2
		mkdir /longterm/zfs_longterm/ledaovro$ii/data2/one
		mkdir /longterm/zfs_longterm/ledaovro$ii/data2/two

	fi
done

#!/bin/bash

if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <src> <dst> <dport> <iters> <tag>" >&2
  exit 1
fi

# map of datasets to bytes in each
declare -A datasets
# KiB
for d in $(seq 0 9); do
    pwr=$((2**$d))
    sz=$((1048576*1024*pwr))
    datasets[1048576x${pwr}KiB]=${sz}
done
# MiB
for d in $(seq 0 9); do
    pwr=$((2**$d))
    sz=$((1048576*1024*1024))
    datasets[$((1048576/$pwr))x${pwr}MiB]=${sz}
done
# GiB
for d in $(seq 0 9); do
    pwr=$((2**$d))
    sz=$((1048576*1024*1024))
    datasets[$((1024/$pwr))x${pwr}GiB]=${sz}
done
# TiB
datasets[1x1TiB]=$((1048576*1024*1024))

# These are the sets we run
declare -a runset
runset=(
#    1048576x1KiB
#    1048576x2KiB
#    1048576x4KiB
#    1048576x8KiB
#    1048576x16KiB
#    1048576x32KiB
#    1048576x64KiB
#    1048576x128KiB
#    1048576x256KiB
#    1048576x512KiB
#    1048576x1MiB
#    524288x2MiB
#    262144x4MiB
#    131072x8MiB
#    65536x16MiB
#    32768x32MiB
#    16384x64MiB
#    8192x128MiB
#    4096x256MiB
#    2048x512MiB
#    1024x1GiB
#    512x2GiB
#    256x4GiB
#    128x8GiB
#    64x16GiB
#    32x32GiB
#    16x64GiB
#    8x128GiB
    4x256GiB
#    2x512GiB
#    1x1TiB
)

SHOST=$1
SPORT=$2
DHOST=$3
DPORT=$4
ITERS=$5
TAG=$6

SSH_CMD="ssh -o StrictHostKeyChecking=no"

OUTDIR=/data/escp_results/${TAG}
SDIR=/data/zettar/zettar/zx/src
DDIR=/data/escp/temp

[[ ! -f $OUTDIR ]] && mkdir -p $OUTDIR

function run_meas() {
    HOST=$1
    PORT=$2
    DST=$3
    $SSH_CMD -p ${PORT} $HOST "mpstat -P ALL 1" &> ${OUTDIR}/${DST}
}

function drop_caches() {
    HOST=$1
    PORT=$2
    $SSH_CMD -p ${PORT} $HOST "echo 3 | sudo tee /proc/sys/vm/drop_caches &> /dev/null"
}

function clean_up() {
    HOST=$1
    PORT=$2
    $SSH_CMD -p ${PORT} $HOST "rm -rf ${DDIR} && mkdir ${DDIR}"
}

for dset in ${runset[@]}; do

    for i in $(seq 1 $ITERS); do
	drop_caches $SHOST $SPORT
	echo "Running ${dset}.${i}"
	run_meas $SHOST $SPORT "src-cpu-${dset}.${i}" &
	run_meas $DHOST $DPORT "dst-cpu-${dset}.${i}" &
	start=$SECONDS
	escp --direct --bits -P ${DPORT} ${SDIR}/${dset} ${DHOST}:${DDIR} &> ${OUTDIR}/${dset}.${i}
	end=$SECONDS
	dur=$((end-start))
	gbps=$(echo "scale=2; ${datasets[$dset]}*8/${dur}/1000000000" | bc -l)
	echo "Result ${dset}.${i} ${dur} ${gbps}" | tee -a ${OUTDIR}/${dset}.${i}
	sleep 2;
	pkill -f "ssh -o"
	clean_up $DHOST $DPORT
	sleep 2;
    done

done

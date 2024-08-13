#!/usr/bin/env bash

# build from clearcase and copy files to flash directory

if [ -z $CLEARCASE_ROOT ]
then
    echo "Please enter view"
    exit
fi

BUILD_CMD="$(cleartool catcs|grep make| sed 's/^#\(.*\)/\1/') 2>&1 | tee build_log"
TAG=${CLEARCASE_ROOT#/view/}
BUILD_DIR=$(eval echo $HOME/ATV/$TAG/android-q-10/out/target/product/*/)

# copy results
echo cp -f $BUILD_DIR/{boot.img,cache.img,dtbo.*.img,super.img,userdata.img,vbmeta.img} ./
cp $BUILD_DIR/{boot.img,cache.img,dtbo.*.img,super.img,userdata.img,vbmeta.img} ./

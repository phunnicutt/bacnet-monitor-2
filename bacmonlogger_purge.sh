#!/bin/bash

LOGNAME=`mktemp` || exit 1

BACMON_HOME=/home/bacmon
BACMON_INI=$BACMON_HOME/BACmon.ini
BACMON_LOGDIR=`cat $BACMON_INI | grep ^logdir: | awk -F:\  '{ print $2 }'`
BACMON_LOGDIRSIZE=`cat $BACMON_INI | grep ^logdirsize: | awk -F:\  '{ print $2 }'`

CHECK=$(du -b -s $BACMON_LOGDIR | awk '{print $1}')

while [ "$CHECK" -gt "$BACMON_LOGDIRSIZE" ]; do
    # remove the oldest file
    FILE=`find $BACMON_LOGDIR/* | head -n 1`
    rm -fv $FILE >> $LOGNAME

    CHECK=$(du -b -s $BACMON_LOGDIR | awk '{print $1}')
done

# if the log file exists, something was deleted
if [ -e $LOGNAME ]; then
    ### email the list of files removed to someone
    rm $LOGNAME
fi


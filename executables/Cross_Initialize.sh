#!/bin/sh
# Cross_Initialize

current=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )

inputstring=""
#Accept Arguments
while [[ "$#" > 1 ]]; do case $1 in
    --config) CONFIG_FILE="$2";;
    --subject) subject_id="$2";;
    --timepoint) timepoint="$2";;
    --inputfile) inputstring="${inputstring} -i $2";;
    *);;
  esac; shift
done

if [[ x${CONFIG_FILE} == x ]] ; then
  echo "CONFIG_FILE is not defined!"
  exit 0
fi

source ${CONFIG_FILE}

if [[ x${FREESURFER_HOME} == x ]] ; then
  echo "FREESURFER_HOME is not defined!"
  exit 1
fi

if [[ x${SUBJECTS_DIR} == x ]] ; then
  echo "SUBJECTS_DIR is not defined!"
  exit 1
fi

if [[ x${MONITOR_DIR} == x ]] ; then
  echo "MONITOR_DIR is not defined!"
  exit 1
fi

export FREESURFER_HOME=$FREESURFER_HOME
export SUBJECTS_DIR=$SUBJECTS_DIR

source ${FREESURFER_HOME}/SetUpFreeSurfer.sh

if [[ ${IS_LONGITUDINAL} == True ]] ; then
  echo "Longitudinal Processing"
  if [[ x${timepoint} == x ]] ; then
    echo "No timepoint specified!"
    exit 1
  else
    subject_id=${subject_id}_${timepoint}
  fi
fi
echo $subject_id

#Create the row
${current}/palantir/palantir update ${MONITOR_DIR} --addrow ${subject_id}
${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Extract --settext "N/A" --setbgcolor "#d2d2d2" --settxtcolor "#f0f0f0" --setbool "False"

#Set to running
${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_Initialize --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"

if [ $HOSTNAME != $DESIRED_HOSTNAME ] ; then
  echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"
  echo "ABORTING PROCESS"
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_Initialize --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"
  exit 1
fi

if recon-all ${inputstring} -subjid ${subject_id} -all ; then
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_Initialize --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"
else
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_Initialize --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"
  exit 1
fi

exit 0

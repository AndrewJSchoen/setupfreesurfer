#!/bin/sh
# Base_maskRerun

current=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )

timepoints=""

#Accept Arguments
while [[ "$#" > 1 ]]; do case $1 in
    --config) CONFIG_FILE="$2";;
    --subject) subject_id="$2";;
    --timepoint) timepoints="${timepoints} $2";;
    -t) timepoints="${timepoints} $2";;
    *);;
  esac; shift
done

inputstring=""
for timepoint in $timepoints ; do
  inputstring="${inputstring} -tp ${subject_id}_${timepoint}"
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

#Update monitor to "Running"
for timepoint in $timepoints ; do
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c Base_maskRerun --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"
done

if [ $HOSTNAME != $DESIRED_HOSTNAME ] ; then
  echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"
  echo "ABORTING PROCESS"
  for timepoint in $timepoints ; do
    ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c Base_maskRerun --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"
  done
  exit 1
fi

if recon-all -base ${subject_id}_base ${inputstring} -autorecon2 -autorecon3 ; then
  for timepoint in $timepoints ; do
    ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c Base_maskRerun --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"
  done
else
  for timepoint in $timepoints ; do
    ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c Base_maskRerun --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"
  done
  exit 1
fi

exit 0

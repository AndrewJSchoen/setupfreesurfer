#!/bin/sh
# Cross_talRerun

current=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

#Accept Arguments
while [[ "$#" > 1 ]]; do case $1 in
    --config) CONFIG_FILE="$2";;
    --subject) subject_id="$2";;
    --timepoint) timepoint="$2";;
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

export $FREESURFER_HOME
export $SUBJECTS_DIR

source ${FREESURFER_HOME}/SetUpFreeSurfer.sh

if [[ ${IS_LONGITUDINAL} == "True" ]] ; then
  if [[ x${timepoint} == x ]] ; then
    echo "No timepoint specified!"
    exit 1
  subject_id=${subject_id}_${timepoint}
  fi
fi

${current}/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_talRerun --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"

if [ $HOSTNAME != $DESIRED_HOSTNAME ] ; then
  echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"
  echo "ABORTING PROCESS"
  ${current}/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_talRerun --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"
  exit 1
fi

if recon-all -subjid ${subject_id} -all ; then
  ${current}/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_talRerun --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"
else
  ${current}/palantir cell ${MONITOR_DIR} -r ${subject_id} -c Cross_talRerun --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"
  exit 1
fi

exit 0

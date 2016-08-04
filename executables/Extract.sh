#!/bin/sh
# Extract

current=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )

subject_ids=""
#Accept Arguments
while [[ "$#" > 1 ]]; do case $1 in
    --config) CONFIG_FILE="$2";;
    --subjectlist) subject_list_file="$2";;
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

if [[ x${ANALYSIS_DIR} == x ]] ; then
  echo "ANALYSIS_DIR is not defined!"
  exit 1
fi

export FREESURFER_HOME=$FREESURFER_HOME
export SUBJECTS_DIR=$SUBJECTS_DIR

source ${FREESURFER_HOME}/SetUpFreeSurfer.sh


if [[ ${IS_LONGITUDINAL} == "True" ]] ; then
  long_subject_ids=""
  for subject_id in $subject_ids ; do
    long_subject_ids="${}"
fi

${current}/palantir/palantir cell ${MONITOR_DIR} -r Project -c Extract --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"

if [ $HOSTNAME != $DESIRED_HOSTNAME ] ; then
  echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"
  echo "ABORTING PROCESS"
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r Project -c Extract --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"
  exit 1
fi
errorcode=0
subjects=""
for subject in `cat ${subject_list_file}` ; do
  subjects="$subjects $subject"
done

cd $SUBJECTS_DIR
cd ../analysis/extracted

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas area --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-desikankilliany-area-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas area --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-desikankilliany-area-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas meancurv --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-desikankilliany-meancurv-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas meancurv --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-desikankilliany-meancurv-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas thickness --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-desikankilliany-thickness-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas thickness --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-desikankilliany-thickness-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas volume --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-desikankilliany-volume-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas volume --parc aparc --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-desikankilliany-volume-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas area --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-destrieux-area-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas area --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-destrieux-area-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas meancurv --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-destrieux-meancurv-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas meancurv --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-destrieux-meancurv-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas thickness --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-destrieux-thickness-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas thickness --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-destrieux-thickness-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi lh --subjects $subjects --delimiter comma --meas volume --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/lh_aparc-destrieux-volume-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if aparcstats2table --hemi rh --subjects $subjects --delimiter comma --meas volume --parc aparc.a2009s --tablefile ${ANALYSIS_DIR}/extracted/rh_aparc-destrieux-volume-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if asegstats2table --subjects $subjects --delimiter comma --stats aseg.stats --tablefile ${ANALYSIS_DIR}/extracted/aseg-volume-table.csv ; then
  errorcode=$((errorcode + 0))
else
  errorcode=$((errorcode + 1))
fi

if [[ $errorcode == 0 ]] ; then
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r Project -c Extract --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"
else
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r Project -c Extract --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"
  exit 1
fi

exit 0

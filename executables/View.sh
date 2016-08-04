#!/bin/sh
# View

current=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )

#Accept Arguments
while [[ "$#" > 1 ]]; do case $1 in
    --config) CONFIG_FILE="$2";;
    --subject) subject_id="$2";;
    --timepoint) timepoints="$timepoints $2";;
    --type) view_type="$2";;
    --phase) phase="$2";;
    *);;
  esac; shift
done

if [[ $phase != "base" ]] ; then
  for timepoint in $timepoints ; do
    timepoint=$timepoint
  done
fi

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

if [[ ${IS_LONGITUDINAL} == "True" ]] ; then
  case $phase in
    cross) fs_id="${subject_id}_${timepoint}" ; monitor_id="${subject_id}_${timepoint}";;
    base) fs_id="${subject_id}_base" ; monitor_id="";;
    long) fs_id="${subject_id}_${timepoint}.long.${subject_id}_base" ; monitor_id="${subject_id}_${timepoint}";;
    *) echo "Phase not recognized! Exiting" ; exit 1;;
  esac
else
  case $phase in
    cross) fs_id="${subject_id}";;
    *) echo "Phase not recognized! Exiting" ; exit 1;;
  esac
fi

case $view_type in
  tal) commandstring="tkregister2 --mgz --s ${fs_id} --fstal --surf orig";;
  mask) commandstring="freeview -v ${fs_id}/mri/T1.mgz ${fs_id}/mri/brainmask.mgz:colormap=heat:opacity=0.4";;
  cp) commandstring="freeview -v ${fs_id}/mri/T1.mgz ${fs_id}/mri/brainmask.mgz ${fs_id}/mri/wm.mgz:colormap=heat:opacity=0.3 -f ${fs_id}/surf/lh.white:edgecolor=yellow ${fs_id}/surf/lh.pial:edgecolor=red ${fs_id}/surf/rh.white:edgecolor=yellow ${fs_id}/surf/rh.pial:edgecolor=red";;
  wm) commandstring="freeview -v ${fs_id}/mri/T1.mgz ${fs_id}/mri/brainmask.mgz ${fs_id}/mri/wm.mgz:opacity=0.5 -f ${fs_id}/surf/lh.white:edgecolor=yellow ${fs_id}/surf/lh.pial:edgecolor=red ${fs_id}/surf/rh.white:edgecolor=yellow ${fs_id}/surf/rh.pial:edgecolor=red";;
  gm) commandstring="freeview -v ${fs_id}/mri/T1.mgz ${fs_id}/mri/brainmask.mgz ${fs_id}/mri/wm.mgz:opacity=0 -f ${fs_id}/surf/lh.white:edgecolor=yellow ${fs_id}/surf/lh.pial:edgecolor=red ${fs_id}/surf/rh.white:edgecolor=yellow ${fs_id}/surf/rh.pial:edgecolor=red";;
  *) echo "Type not recognized! Exiting" ; exit 1;;
esac

cd $SUBJECTS_DIR

if [[ $view_type == "cp" ]] ; then
  if [[ -e ${fs_id}/tmp/control.dat ]] ; then
    commandstring="${commandstring} -c ${fs_id}/tmp/control.dat"
  fi
fi

if [[ $phase == "base" ]] ; then
  for timepoint in $timepoints ; do
    ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c View --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Opened ${view_type} viewing for ${phase}"
  done
else
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${monitor_id} -c View --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Opened ${view_type} viewing for ${phase}"
fi
echo $commandstring
eval $commandstring

if [[ $phase == "base" ]] ; then
  for timepoint in $timepoints ; do
    ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${subject_id}_${timepoint} -c View --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Closed"
  done
else
  ${current}/palantir/palantir cell ${MONITOR_DIR} -r ${monitor_id} -c View --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Closed"
fi

exit 0

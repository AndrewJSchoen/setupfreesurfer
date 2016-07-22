#!/usr/bin/env python
import sys
import os
import shutil
import subprocess
import math
import socket
import string
from docopt.docopt import docopt
from palantir import palantir

Version = "0.1.1"
doc = """
Setup FreeSurfer.

Usage:
  setupfreesurfer [options] (--data_dir <dir> | -d <dir>) (--code_dir <dir> | -c <dir>) [(--freesurfer_home <dir> | -f <dir>)] [--host <host>]

Options:
  -h --help                             Show this screen.
  -v --version                          Show the current version.
  -l --longitudinal                     Specify longitudinal processing. [default: False]
  -d <dir> --data_dir <dir>             SUBJECTS_DIR will be a sub-directory, allong with an analysis directory.
  -c <dir> --code_dir <dir>             Where the code should be placed.
  -f <dir> --freesurfer_home <dir>      By default, FREESURFER_HOME env variable. Specify otherwise if needed. [default: None]
  --host <host>                         Optional. Require running from a specific host.
                                        Specify "current" to use the current host. [default: None]
"""

#------------------------------------
#    Utility
#------------------------------------

def get_src():
    return os.path.abspath(os.path.join(os.path.dirname( __file__ )))

def idify(name):
    valid_chars = "-_.{0}{1}".format(string.ascii_letters, string.digits)
    returnid = ''.join(c for c in name if c in valid_chars)
    return returnid

def clean_path(path):
    return os.path.realpath(os.path.expanduser(path))

def exists(path):
    return os.path.exists(os.path.realpath(os.path.expanduser(path)))

def system_call(command):
  p = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, shell=False)
  return p.stdout.read()

def load_file(path):
    text = ""
    with open(clean_path(path), "r") as text_file:
        text = text_file.read()
    return text

def write_file(path, content):
    with open(clean_path(path), "w") as text_file:
        text_file.write(content)


#------------------------------------
#    Classes
#------------------------------------

class Template(object):
    """
    Template Class

    Methods:
        render_script
        render_submit
    """
    def __init__(self, project):
        self.subjects_dir = project.subjects_dir
        self.code_dir = project.code_dir
        self.analysis_dir = project.analysis_dir
        self.monitor_dir = project.monitor_dir
        self.submit_dir = project.submit_dir
        self.log_dir = project.log_dir
        self.script_dir = project.script_dir
        self.freesurfer_home = project.freesurfer_home
        self.is_longitudinal = project.is_longitudinal
        self.host = project.host
        self.palantir_path = get_src() + "/palantir/palantir"

    def render_script(self, script_class):
        lines = []
        lines.extend([
        "#!/bin/sh",
        "# "+script_class.name,
        "export FREESURFER_HOME="+self.freesurfer_home,
        "source $FREESURFER_HOME/SetUpFreeSurfer.sh",
        "export SUBJECTS_DIR="+self.subjects_dir,
        "",
        "starttime=$(date +%s)",
        "curtime=$(date +%FT%R:%S)",
        "",
        "# Accept Arguments"
        ])
        if (script_class.level == 'cross' and self.is_longitudinal) or script_class.level == 'long':
            lines.extend([
            "idvar=$1",
            "timevar=$2",
            "othervars=${@:3}",
            "targetvar=${idvar}_${timevar}"
            ])
        elif script_class.level == 'cross':
            lines.extend([
            "idvar=$1",
            "othervars=${@:2}",
            "targetvar=${idvar}"
            ])
        elif script_class.level == 'base':
            lines.extend([
            "idvar=$1",
            "othervars=${@:2}",
            "targetvar=${idvar}_base"
            ])
        else:
            lines.extend([
            "vars=$@",
            "targetvar=Project"
            ])
        if script_class.name == 'Cross_Initialize' or script_class.name == 'Base_Initialize':
            flag_lookup={"Cross_Initialize": "-i", "Base_Initialize": "-tp"}
            lines.extend([
            "for i in $othervars ; do",
            '  inputstring="${inputstring} '+flag_lookup[script_class.name]+' ${i}"',
            "done"
            ])
        lines.extend(["","errorcode=0",""])

        if script_class.name == 'Cross_Initialize':
            lines.append(self.palantir_path+" update "+self.monitor_dir+" --addrow $targetvar")
        if "Base" in script_class.name:
            lines.extend([
            "  for t in $othervars ; do",
            "    "+self.palantir_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"',
            "  done"
            ])
        else:
            lines.extend([
                self.palantir_path+' cell '+self.monitor_dir+' -r $targetvar -c '+script_class.name+' --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"',""
                ])
        if script_class.requires_host == True and "Base" in script_class.name:
            lines.extend([
            "if [ $HOSTNAME != "+self.host+" ] ; then",
            'echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"',
            'echo "ABORTING PROCESS"',
            self.palantir_path+' cell '+self.monitor_dir+' -r $targetvar -c '+script_class.name+' --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"',
            "exit 1",
            "fi"
            ])
        elif script_class.requires_host == True:
            lines.extend([
            "if [ $HOSTNAME != "+self.host+" ] ; then",
            'echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"',
            'echo "ABORTING PROCESS"',
            "  for t in $othervars ; do",
            "    "+self.palantir_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"',
            "  done",
            "exit 1",
            "fi"
            ])
        for step in script_class.steps:
            if script_class.is_process == True:
                lines.extend([
                "if "+step+" ; then",
                "  errorcode=$((errorcode + 0))",
                "else"
                ])
                if script_class.level == 'base':
                    lines.extend([
                    "  for t in $othervars ; do",
                    "    "+self.palantir_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"',
                    "  done"
                    ])
                else:
                    lines.append("  "+self.palantir_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"')
                lines.extend(["  exit 1","fi",""])
            else:
                lines.append(step)

        lines.extend([
        "endtime=$(date +%s)",
        "totaltime=$((endtime - starttime))",
        "",
        "if [[ ${errorcode} == 0 ]] ; then"
        ])
        if script_class.is_process and "Base" in script_class.name:
            lines.extend([
            "  for t in $othervars ; do",
            "    "+self.palantir_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"',
            "  done"])
        elif script_class.is_process:
            lines.append("  "+self.palantir_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"')
        elif "Base" in script_class.name:
            lines.extend([
            "  for t in $othervars ; do",
            "    "+self.palantir_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"',
            "  done"])
        else:
            lines.append("  "+self.palantir_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Inactive" --setanimate "none" --setbgcolor "#F0F0F0" --settxtcolor "#969696" --addnote "Finished')

        lines.extend([
        "fi",
        "",
        'echo "'+script_class.name+' took $totaltime seconds"',
        "exit 0"
        ])
        script_render = "\n".join(lines)
        return script_render

    def render_submit(self, script_class):
        lines = []
        lines.extend([
        "Universe=vanilla",
        "getenv=True",
        "request_memory="+str(script_class.memory),
        "initialdir="+self.subjects_dir,
        "Executable="+self.script_dir+script_class.executable_name,
        "Log="+self.log_dir+script_class.log_name,
        "Output="+self.log_dir+script_class.out_name,
        "Error="+self.log_dir+script_class.err_name
        ])
        if (script_class.level == 'cross' and self.is_longitudinal) or script_class.level == 'long':
            lines.extend([
            "target=$(id)_$(time)",
            "arguments=$(id) $(time) $(args)"
            ])
        elif script_class.level == 'cross' or script_class.level == "base":
            lines.extend([
            "target=$(id)",
            "arguments=$(id) $(args)"
            ])
        else:
            lines.extend([
            "target=Project"
            "arguments=$(subjects)"
            ])
        lines.append("Queue")
        submit_render = "\n".join(lines)
        return submit_render

class Project(object):
    """
    Project class
    Contains scripts, and handles creating the required directories.

    Properties:
        data_dir
        subjects_dir
        analysis_dir
        code_dir
        freesurfer_home
        scripts
        dirs
        script_template
        submit_template

    Methods:
        create_directories
        write_scripts
        write_submits
        create_monitor
    """
    def __init__(self, data_dir, code_dir, freesurfer_home, is_longitudinal=False, host=None):

        self.data_dir = data_dir
        self.subjects_dir = data_dir + "/subjects/"
        self.analysis_dir = data_dir + "/analysis/"
        self.code_dir = code_dir
        self.monitor_dir = code_dir + "/monitor/"
        self.script_dir = code_dir + "/scripts/"
        self.submit_dir = code_dir + "/submit/"
        self.log_dir = code_dir + "/logs/"
        self.freesurfer_home = freesurfer_home
        self.is_longitudinal = is_longitudinal
        self.host = host
        if self.host == None:
            self.requires_host = False
        else:
            self.requires_host = True

        #Template
        self.template = Template(self)

        #Define Directories
        self.dirs = [
        self.code_dir,
        self.script_dir,
        self.log_dir,
        self.submit_dir,
        self.data_dir,
        self.subjects_dir,
        self.analysis_dir,
        self.analysis_dir + "/wholebrain/",
        self.analysis_dir + "/extracted/",
        ]

        #Define scripts
        self.scripts = []
        self.scripts.extend([
            Script("Cross_Initialize", "cross", self, is_process=True, steps=["recon-all ${inputstring} -subjid ${targetvar} -all"], requires_host=self.requires_host),
            Script("Cross_Restart", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -clean -all"], requires_host=self.requires_host),
            Script("Cross_talEdit", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -all"], requires_host=self.requires_host),
            Script("Cross_maskEdit", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -autorecon2 -autorecon3"], requires_host=self.requires_host),
            Script("Cross_cpEdit", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -autorecon2-cp -autorecon3"], requires_host=self.requires_host),
            Script("Cross_wmEdit", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -autorecon2-wm -autorecon3"], requires_host=self.requires_host),
            Script("Cross_gmEdit", "cross", self, is_process=True, steps=["recon-all -subjid ${targetvar} -autorecon-pial"], requires_host=self.requires_host)
        ])
        if self.is_longitudinal:
            self.scripts.extend([
                Script("Base_Initialize", "base", self, is_process=True, steps=["recon-all ${inputstring} -base ${targetvar} -all"], requires_host=self.requires_host),
                Script("Base_Restart", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -clean -all"], requires_host=self.requires_host),
                Script("Base_talEdit", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -all"], requires_host=self.requires_host),
                Script("Base_maskEdit", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -autorecon2 -autorecon3"], requires_host=self.requires_host),
                Script("Base_cpEdit", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -autorecon2-cp -autorecon3"], requires_host=self.requires_host),
                Script("Base_wmEdit", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -autorecon2-wm -autorecon3"], requires_host=self.requires_host),
                Script("Base_gmEdit", "base", self, is_process=True, steps=["recon-all -base ${targetvar} -autorecon-pial"], requires_host=self.requires_host),
                Script("Long_Initialize", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -all"], requires_host=self.requires_host),
                Script("Long_Restart", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -clean -all"], requires_host=self.requires_host),
                Script("Long_talEdit", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -all"], requires_host=self.requires_host),
                Script("Long_maskEdit", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -autorecon2 -autorecon3"], requires_host=self.requires_host),
                Script("Long_cpEdit", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -autorecon2-cp -autorecon3"], requires_host=self.requires_host),
                Script("Long_wmEdit", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -autorecon2-wm -autorecon3"], requires_host=self.requires_host),
                Script("Long_gmEdit", "long", self, is_process=True, steps=["recon-all -long ${targetvar} ${idvar}_base -autorecon-pial"], requires_host=self.requires_host),
            ])
        self.scripts.append(Script("Extract", "project", self, is_process=True, steps=["aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas area --parc aparc --tablefile {0}/extracted/lh_aparc-desikankilliany-area-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas area --parc aparc --tablefile {0}/extracted/rh_aparc-desikankilliany-area-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas meancurv --parc aparc --tablefile {0}/extracted/lh_aparc-desikankilliany-meancurv-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas meancurv --parc aparc --tablefile {0}/extracted/rh_aparc-desikankilliany-meancurv-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas thickness --parc aparc --tablefile {0}/extracted/lh_aparc-desikankilliany-thickness-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas thickness --parc aparc --tablefile {0}/extracted/rh_aparc-desikankilliany-thickness-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas volume --parc aparc --tablefile {0}/extracted/lh_aparc-desikankilliany-volume-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas volume --parc aparc --tablefile {0}/extracted/rh_aparc-desikankilliany-volume-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas area --parc aparc.a2009s --tablefile {0}/extracted/lh_aparc-destrieux-area-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas area --parc aparc.a2009s --tablefile {0}/extracted/rh_aparc-destrieux-area-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas meancurv --parc aparc.a2009s --tablefile {0}/extracted/lh_aparc-destrieux-meancurv-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas meancurv --parc aparc.a2009s --tablefile {0}/extracted/rh_aparc-destrieux-meancurv-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas thickness --parc aparc.a2009s --tablefile {0}/extracted/lh_aparc-destrieux-thickness-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas thickness --parc aparc.a2009s --tablefile {0}/extracted/rh_aparc-destrieux-thickness-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi lh --subjects $vars --delimiter comma --meas volume --parc aparc.a2009s --tablefile {0}/extracted/lh_aparc-destrieux-volume-table.csv".format(self.analysis_dir),
        "aparcstats2table --hemi rh --subjects $vars --delimiter comma --meas volume --parc aparc.a2009s --tablefile {0}/extracted/rh_aparc-destrieux-volume-table.csv".format(self.analysis_dir),
        "asegstats2table --subjects $vars --delimiter comma --stats aseg.stats --tablefile {0}/extracted/aseg-volume-table.csv".format(self.analysis_dir)], requires_host=self.requires_host))

        self.scripts.extend([
            Script("Cross_talView", "cross", self, is_process=False, steps=["tkregister2 --mgz --s ${{targetvar}} --fstal --surf orig".format(self.subjects_dir)], requires_host=False),
            Script("Cross_maskView", "cross", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(self.subjects_dir)], requires_host=False),
            Script("Cross_cpView", "cross", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red -c {0}${{targetvar}}/tmp/control.dat".format(self.subjects_dir)], requires_host=False),
            Script("Cross_wmView", "cross", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0.5 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False),
            Script("Cross_gmView","cross", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False)
        ])
        if self.is_longitudinal:
            self.scripts.extend([
                Script("Base_talView", "base", self, is_process=False, steps=["tkregister2 --mgz --s ${{targetvar}} --fstal --surf orig".format(self.subjects_dir)], requires_host=False),
                Script("Base_maskView", "base", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(self.subjects_dir)], requires_host=False),
                Script("Base_cpView", "base", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red -c {0}${{targetvar}}/tmp/control.dat".format(self.subjects_dir)], requires_host=False),
                Script("Base_wmView", "base", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0.5 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False),
                Script("Base_gmView","base", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False),
                Script("Long_talView", "long", self, is_process=False, steps=["tkregister2 --mgz --s ${{targetvar}} --fstal --surf orig".format(self.subjects_dir)], requires_host=False),
                Script("Long_maskView", "long", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(self.subjects_dir)], requires_host=False),
                Script("Long_cpView", "long", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red -c {0}${{targetvar}}/tmp/control.dat".format(self.subjects_dir)], requires_host=False),
                Script("Long_wmView", "long", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0.5 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False),
                Script("Long_gmView","long", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}${{targetvar}}/mri/brainmask.mgz {0}${{targetvar}}/mri/wm.mgz:opacity=0 -f {0}${{targetvar}}/surf/lh.white:edgecolor=yellow {0}${{targetvar}}/surf/lh.pial:edgecolor=red {0}${{targetvar}}/surf/rh.white:edgecolor=yellow {0}${{targetvar}}/surf/rh.pial:edgecolor=red".format(self.subjects_dir)], requires_host=False)
            ])

    def create_directories(self):
        for directory in self.dirs:
            try:
                os.makedirs(directory)
            except:
                pass

    def write_scripts(self):
        for script in self.scripts:
            script.write_script()

    def write_submits(self):
        for script in self.scripts:
            if script.is_process:
                script.write_submit()

    def create_monitor(self):
        if exists(self.monitor_dir):
            shutil.rmtree(self.monitor_dir)
        palantir.create(self.monitor_dir, "FreeSurfer")
        palantir.update(self.monitor_dir, add_rows=["Project"], add_columns=[script.name for script in self.scripts])
        for script in self.scripts:
            if script.level != "project":
                palantir.cell(self.monitor_dir, row_id="Project", column_id=script.name, text="N/A", background_color="#d2d2d2", text_color="#f0f0f0", boolean="False")


class Script(object):
    """
    Script class.

    """
    def __init__(self, name, level, project, is_process=True, steps=[], memory=3072, requires_host=False):
        self.name = idify(name)
        self.level = level
        self.memory = memory
        self.is_process = is_process
        self.requires_host = requires_host
        self.steps = steps

        self.executable_name = self.name+".sh"
        self.submit_name = self.name+".txt"
        self.log_name = self.name+"_$(target)_log.txt"
        self.out_name = self.name+"_$(target)_out.txt"
        self.err_name = self.name+"_$(target)_err.txt"

        self.executable_path = project.script_dir+self.executable_name
        self.submit_path = project.submit_dir+self.submit_name

        self.script_text = project.template.render_script(self)
        self.submit_text = project.template.render_submit(self)

    def write_script(self):
        write_file(self.executable_path, self.script_text)
        os.chmod(self.executable_path, os.stat(self.executable_path).st_mode | 0111)
        pass

    def write_submit(self):
        write_file(self.submit_path, self.submit_text)
        pass


def run(args):

  # Checking $FREESURFER_HOME
  if args["--freesurfer_home"] in [None,"None"]:
      env_home = os.environ.get('FREESURFER_HOME')
      if exists(env_home):
          args["--freesurfer_home"] = clean_path(env_home)
      else:
          print("$FREESURFER_HOME is not defined as an environment variable.\nEither define the variable in the environment, or specify it in the command (see help).")
          print(clean_path(env_home))
          sys.exit(1)

  # Checking Host
  if args["--host"] == "current":
      args["--host"] = socket.gethostname()
  elif args["--host"] == "None":
      args["--host"] = None

  # Checking Flags
  if args["--longitudinal"] in ["True", "true", True]:
      args["--longitudinal"] = True
  elif args["--longitudinal"] in ["False", "false", False]:
      args["--longitudinal"] = False
  else:
      args["--longitudinal"] = False

  # Setup
  project = Project(data_dir=clean_path(args["--data_dir"]), code_dir=clean_path(args["--code_dir"]), freesurfer_home=clean_path(args["--freesurfer_home"]), is_longitudinal=args["--longitudinal"], host=args["--host"])
  project.create_directories()
  project.write_scripts()
  project.write_submits()
  project.create_monitor()
  print("Setup Complete!")

#------------------------------------
#    Main
#------------------------------------

if __name__ == '__main__':
    args = docopt(doc, version='Setup FreeSurfer v{0}'.format(Version))
    run(args)

#!/usr/bin/env python
import sys
import os
import shutil
import subprocess
import math
import socket
import string
from docopt.docopt import docopt
from dash import dash

Version = "0.1"
doc = """
Setup FreeSurfer.

Usage:
  setupfreesurfer.py [options] (--data_dir <dir> | -d <dir>) (--code_dir <dir> | -c <dir>) [(--freesurfer_home <dir> | -f <dir>)] [--host <host>]

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
        self.dash_path = get_src() + "/dash/dash.py"

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
            lines.append(self.dash_path+" update "+self.monitor_dir+" --addrow $targetvar")
        lines.extend([
        self.dash_path+' cell '+self.monitor_dir+' -r $targetvar -c '+script_class.name+' --settext "Running" --setanimate "bars" --setbgcolor "#efd252" --settxtcolor "#ec6527" --addnote "Started running"',
        ""
        ])
        if script_class.requires_host == True:
            lines.extend([
            "if [ $HOSTNAME != "+self.host+" ] ; then",
            'echo "ERROR: NOT ON CORRECT HOST FOR RUNNING FREESURFER"',
            'echo "ABORTING PROCESS"',
            self.dash_path+' cell '+self.monitor_dir+' -r $targetvar -c '+script_class.name+' --settext "Host Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b"',
            "exit 1",
            "fi"
            ])
        for step in script_class.steps:
            lines.extend([
            "if "+step+" ; then",
            "  errorcode=$((errorcode + 0))",
            "else"
            ])
            if script_class.level == 'base':
                lines.extend([
                "  for t in $othervars ; do",
                "    "+self.dash_path+' cell '+self.monitor_dir+' -r ${idvar}_${t} -c '+script_class.name+' --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"',
                "  done"
                ])
            else:
                lines.append("  "+self.dash_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Error" --setanimate "toggle" --setbgcolor "#cb3448" --settxtcolor "#791f2b" --addnote "Error"')
            lines.extend(["  exit 1","fi",""])
        lines.extend([
        "endtime=$(date +%s)",
        "totaltime=$((endtime - starttime))",
        "",
        "if [[ ${errorcode} == 0 ]] ; then"
        ])
        if script_class.is_process:
            lines.append("  "+self.dash_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Finished" --setanimate "none" --setbgcolor "#009933" --settxtcolor "#004c19" --addnote "Successfully finished"')
        else:
            lines.append("  "+self.dash_path+' cell '+self.monitor_dir+' -r ${targetvar} -c '+script_class.name+' --settext "Inactive" --setanimate "none" --setbgcolor "#F0F0F0" --settxtcolor "#969696" --addnote "Finished')

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
            Script("Cross_maskView", "cross", self, is_process=False, steps=["freeview -v {0}${{targetvar}}/mri/T1.mgz {0}/subjects/${{targetvar}}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(self.subjects_dir)], requires_host=False),
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
            script.write_submit()

    def create_monitor(self):
        if exists(self.monitor_dir):
            shutil.rmtree(self.monitor_dir)
        dash.create(self.monitor_dir, "FreeSurfer")
        dash.update(self.monitor_dir, add_rows=["Project"], add_columns=[script.name for script in self.scripts])
        for script in self.scripts:
            if script.level != "project":
                dash.cell(self.monitor_dir, row_id="Project", column_id=script.name, text="N/A", background_color="#d2d2d2", text_color="#f0f0f0", boolean="False")


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

    # def __as_dict__(self):
    #     dictionary = {
    #     "script_name": self.name,
    #     "level": self.level,
    #     "is_process": self.is_process,
    #     "requires_host": self.requires_host,
    #     "rel_executable_path": self.rel_executable_path,
    #     "rel_submit_path": self.rel_submit_path,
    #     "rel_log_path": self.rel_log_path,
    #     "rel_out_path": self.rel_out_path,
    #     "rel_err_path": self.rel_err_path,
    #     }
    #     return dictionary

    def write_script(self):
        write_file(self.executable_path, self.script_text)
        os.chmod(self.executable_path, os.stat(self.executable_path).st_mode | 0111)
        pass

    def write_submit(self):
        write_file(self.submit_path, self.submit_text)
        pass

#============================================================================
#============ String Library ================================================

# def defineScripts(arguments):
#     ScriptHeader = """#!/bin/sh
#
# export FREESURFER_HOME=/apps/x86_64_sci7/freesurfer-latest
# source $FREESURFER_HOME/SetUpFreeSurfer.sh
# export SUBJECTS_DIR={0}/subjects
#
# STARTTIME=$(date +%s)
# curtime=$(date +%FT%R:%S)
# """.format(arguments["FreeSurferDir"])
#     if arguments["IsLongitudinal"]:
#         substring = "${subid}_${time}"
#         subarglist = ["subid=$1", "time=$2"]
#         allotherargs = "${@:3}"
#         allbutfirstarg = "${@:2}"
#     else:
#         substring = "${subid}"
#         subarglist = ["subid=$1"]
#         allotherargs = "${@:2}"
#         allbutfirstarg = allotherargs
#
#     orig =      {"Name": "Orig",
#                  "InputLines": subarglist + ["inputstring=''", 'for i in {0} ; do inputstring="${{inputstring}} -i ${{i}}" ; done'.format(allotherargs)],
#                  "Steps": ["recon-all ${{inputstring}} -subjid {0} -all".format(substring)]}
#     restart =   {"Name": "Restart",
#                  "InputLines": subarglist,
#                  "Steps": ["recon-all -clean -subjid {0} -all".format(substring)]}
#     base_gen =  {"Name": "Base",
#                  "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                  "Steps": ["recon-all -base ${subid}_base ${inputstring} -all"]}
#     long_gen =  {"Name": "Long",
#                  "InputLines": subarglist,
#                  "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -all"]}
#
#
#     cross_talEdit =   {"Name": "Cross_talEdit",
#                        "InputLines": subarglist,
#                        "Steps": ["recon-all -subjid {0} -all".format(substring)]}
#
#     cross_maskEdit = {"Name": "Cross_maskEdit",
#                          "InputLines": subarglist,
#                          "Steps": ["recon-all -autorecon2 -autorecon3 -subjid {0}".format(substring)]}
#     cross_cpEdit =   {"Name": "Cross_cpEdit",
#                          "InputLines": subarglist,
#                          "Steps": ["recon-all -autorecon2-cp -autorecon3 -subjid {0}".format(substring)]}
#     cross_wmEdit =   {"Name": "Cross_wmEdit",
#                          "InputLines": subarglist,
#                          "Steps": ["recon-all -autorecon2-wm -autorecon3 -subjid {0}".format(substring)]}
#     cross_gmEdit =   {"Name": "Cross_gmEdit",
#                          "InputLines": subarglist,
#                          "Steps": ["recon-all -autorecon-pial -subjid {0} -all".format(substring)]}
#
#     base_talEdit = {"Name": "Base_talEdit",
#                         "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                         "Steps": ["recon-all -base ${subid}_base ${inputstring} -all"]}
#
#     base_maskEdit = {"Name": "Base_maskEdit",
#                         "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                         "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2 -autorecon3"]}
#     base_cpEdit =   {"Name": "Base_cpEdit",
#                         "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                         "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2-cp -autorecon3"]}
#     base_wmEdit =   {"Name": "Base_wmEdit",
#                         "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                         "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2-wm -autorecon3"]}
#     base_gmEdit =   {"Name": "Base_gmEdit",
#                         "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
#                         "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon-pial"]}
#
#     long_talEdit = {"Name": "Long_talEdit",
#                         "InputLines": subarglist,
#                         "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -all"]}
#     long_maskEdit = {"Name": "Long_maskEdit",
#                         "InputLines": subarglist,
#                         "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2 -autorecon3"]}
#     long_cpEdit =   {"Name": "Long_cpEdit",
#                         "InputLines": subarglist,
#                         "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2-cp -autorecon3"]}
#     long_wmEdit =   {"Name": "Long_wmEdit",
#                         "InputLines": subarglist,
#                         "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2-wm -autorecon3"]}
#     long_gmEdit =   {"Name": "Long_gmEdit",
#                         "InputLines": subarglist,
#                         "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon-pial"]}
#
#     extractvals = {"Name": "ExtractVals",
#                    "InputLines": ["subjectslist=$@"],
#                    "Steps": ["aparcstats2table --hemi lh --subjects $subjectslist --meas area --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-area-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi lh --subjects $subjectslist --meas meancurv --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-meancurv-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi lh --subjects $subjectslist --meas thickness --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-thickness-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi lh --subjects $subjectslist --meas volume --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-volume-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi rh --subjects $subjectslist --meas area --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-area-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi rh --subjects $subjectslist --meas meancurv --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-meancurv-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi rh --subjects $subjectslist --meas thickness --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-thickness-table.csv".format(arguments["FreeSurferDir"]),
#                              "aparcstats2table --hemi rh --subjects $subjectslist --meas volume --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-volume-table.csv".format(arguments["FreeSurferDir"]),
#                              "segstats2table --subjects $subjectslist --stats aseg.stats --tablefile {0}/analysis/atlas-extracted/aseg-vol-table.csv".format(arguments["FreeSurferDir"])]}
#
#
#     cross_talView = {"Name": "Cross_talView",
#                      "InputLines": subarglist,
#                      "Steps": ["tkregister2 --mgz --s {0} --fstal --surf orig".format(substring)]}
#
#     cross_maskView = {"Name": "Cross_maskView",
#                      "InputLines": subarglist,
#                      "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"], substring)]}
#
#     cross_cpView = {"Name": "Cross_cpView",
#                      "InputLines": subarglist,
#                      "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz {0}/subjects/{1}/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/{1}/surf/lh.white:edgecolor=yellow {0}/subjects/{1}/surf/lh.pial:edgecolor=red {0}/subjects/{1}/surf/rh.white:edgecolor=yellow {0}/subjects/{1}/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}
#
#     cross_wmView = {"Name": "Cross_wmView",
#                      "InputLines": subarglist,
#                      "Steps": [.format(arguments["FreeSurferDir"], substring)]}
#
#     cross_gmView = {"Name": "Cross_gmView",
#                      "InputLines": subarglist,
#                      "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz {0}/subjects/{1}/mri/wm.mgz:opacity=0 -f {0}/subjects/{1}/surf/lh.white:edgecolor=yellow {0}/subjects/{1}/surf/lh.pial:edgecolor=red {0}/subjects/{1}/surf/rh.white:edgecolor=yellow {0}/subjects/{1}/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}
#
#
#     base_talView = {"Name": "Base_talView",
#                      "InputLines": ["subid=$1"],
#                      "Steps": ["tkregister2 --mgz --s ${subid}_base --fstal --surf orig"]}
#
#     base_maskView = {"Name": "Base_maskView",
#                      "InputLines": ["subid=$1"],
#                      "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"])]}
#
#     base_cpView = {"Name": "Base_cpView",
#                      "InputLines": ["subid=$1"],
#                      "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}
#
#     base_wmView = {"Name": "Base_wmView",
#                    "InputLines": ["subid=$1"],
#                    "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:opacity=0.5 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}
#
#     base_gmView = {"Name": "Base_gmView",
#                    "InputLines": ["subid=$1"],
#                    "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:opacity=0 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}
#
#
#     long_talView = {"Name": "Long_talView",
#                     "InputLines": subarglist,
#                     "Steps": ["tkregister2 --mgz --s {0}.long.${{subid}}_base --fstal --surf orig".format(substring)]}
#
#     long_maskView = {"Name": "Long_maskView",
#                      "InputLines": subarglist,
#                      "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"], substring)]}
#
#     long_cpView = {"Name": "Long_cpView",
#                      "InputLines": subarglist,
#                      "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}
#
#     long_wmView = {"Name": "Long_wmView",
#                    "InputLines": subarglist,
#                    "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:opacity=0.5 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}
#
#     long_gmView = {"Name": "Long_gmView",
#                    "InputLines": subarglist,
#                    "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:opacity=0 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}
#
#     if arguments["IsLongitudinal"]:
#         ScriptList = [orig, restart, base_gen, long_gen, cross_talEdit, cross_maskEdit, cross_cpEdit, cross_wmEdit, cross_gmEdit, base_talEdit, base_maskEdit, base_cpEdit, base_wmEdit, base_gmEdit, long_talEdit, long_maskEdit, long_cpEdit, long_wmEdit, long_gmEdit, extractvals, cross_talView, cross_maskView, cross_cpView, cross_wmView, cross_gmView, base_talView, base_maskView, base_cpView, base_wmView, base_gmView, long_talView, long_maskView, long_cpView, long_wmView, long_gmView]
#     else:
#         ScriptList = [orig, restart, cross_talEdit, cross_maskEdit, cross_cpEdit, cross_wmEdit, cross_gmEdit, extractvals, cross_talView, cross_maskView, cross_cpView, cross_wmView, cross_gmView]
#
#     return ScriptHeader, ScriptList


    # os.chmod(arguments["FreeSurferDir"]+"/scripts/"+script["Name"]+".sh", os.stat(arguments["FreeSurferDir"]+"/scripts/"+script["Name"]+".sh").st_mode | 0111)

#============================================================================
#============ Submit Writing ================================================

# def writeSubmit(script, arguments):
#     print(script["Name"])
#     standardheader = """Universe=vanilla
# getenv=True
# request_memory=3072
# initialdir={0}/subjects
# Executable={0}/scripts/{1}.sh
# Log={0}/scripts/condorlogs/{1}_$(target)_log.txt
# Output={0}/scripts/condorlogs/{1}_$(target)_out.txt
# Error={0}/scripts/condorlogs/{1}_$(target)_err.txt
# Notification=Error
# """.format(arguments["FreeSurferDir"], script["Name"])
#     if script["Name"] == "ExtractVals":
#         subjectlist = []
#         if arguments["IsLongitudinal"]:
#             for rowindex, row in arguments["InputFile"].iterrows():
#                 subjectlist.append("{0}_{1}".format(rowindex, row["Timepoint"]))
#         else:
#             for rowindex, row in arguments["InputFile"].iterrows():
#                 subjectlist.append("{0}".format(rowindex))
#         queuelist = ["\ntarget=Project\narguments=" + '"' + " ".join(subjectlist) + '"' + "\nQueue\n"]
#     elif script["Name"] == "Orig":
#         queuelist = []
#         for rowindex, row in arguments["InputFile"].iterrows():
#             filesheaders = []
#             subjexistingfiles = []
#             rowindices = list(row.index)
#             for key in rowindices:
#                 if "File" in key:
#                     filesheaders.append(key)
#             for fileheader in filesheaders:
#                 if row[fileheader] != None:
#                     subjexistingfiles.append(row[fileheader])
#             subjarguments = [rowindex]
#             if arguments["IsLongitudinal"]:
#                 subjarguments.append(str(row["Timepoint"]))
#             subjarguments.extend(subjexistingfiles)
#             if arguments["IsLongitudinal"]:
#                 queuelist.append('\ntarget={0}_{1}\narguments="{2}"\nQueue\n'.format(rowindex, row["Timepoint"], " ".join(subjarguments)))
#             else:
#                 queuelist.append('\ntarget={0}\narguments="{1}"\nQueue\n'.format(rowindex, " ".join(subjarguments)))
#     elif script["Name"] in ["Restart", "Cross_talEdit", "Cross_maskEdit", "Cross_cpEdit", "Cross_wmEdit", "Cross_gmEdit", "Long", "Long_talEdit", "Long_maskEdit", "Long_cpEdit", "Long_wmEdit", "Long_gmEdit"]:
#         queuelist = []
#         for rowindex, row in arguments["InputFile"].iterrows():
#             if arguments["IsLongitudinal"]:
#                 queuelist.append('\ntarget={0}_{1}\narguments="{0} {1}"\nQueue\n'.format(rowindex, row["Timepoint"]))
#             else:
#                 queuelist.append('\ntarget={0}\narguments="{0}"\nQueue\n'.format(rowindex))
#     else:
#         queuelist = []
#         uniquesubjects = set(list(arguments["InputFile"].index))
#         for uniquesubject in uniquesubjects:
#             subjectframesubsection = arguments["InputFile"][(arguments["InputFile"].index == str(uniquesubject))]
#             intsubjecttimepoints = list(subjectframesubsection["Timepoint"])
#             subjecttimepoints = []
#             for subjecttimepoint in intsubjecttimepoints:
#                 subjecttimepoints.append(str(subjecttimepoint))
#             subjarguments = [uniquesubject] + subjecttimepoints
#             queuelist.append("\ntarget="+uniquesubject+"\narguments=" + '"' + " ".join(subjarguments) + '"' + "\nQueue\n")
#     condorsubmitlist = [standardheader] + queuelist
#     condorsubmitcontents = "\n".join(condorsubmitlist)
#     writeFile(condorsubmitcontents, arguments["FreeSurferDir"]+"/scripts/condorsubmit/cs_"+script["Name"]+".txt")


#------------------------------------
#    Run
#------------------------------------

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
  print(clean_path(args["--data_dir"]))
  print(clean_path(args["--code_dir"]))
  print(clean_path(args["--freesurfer_home"]))
  print(args["--host"])
  project = Project(data_dir=clean_path(args["--data_dir"]), code_dir=clean_path(args["--code_dir"]), freesurfer_home=clean_path(args["--freesurfer_home"]), is_longitudinal=args["--longitudinal"], host=args["--host"])
  project.create_directories()
  project.write_scripts()
  project.write_submits()
  project.create_monitor()

#------------------------------------
#    Main
#------------------------------------

if __name__ == '__main__':
    args = docopt(doc, version='Setup FreeSurfer v{0}'.format(Version))
    print(args)
    run(args)

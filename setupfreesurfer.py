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

Version = "0.2"
doc = """
Setup FreeSurfer.

Usage:
  setupfreesurfer [options] (--data_dir <dir> | -d <dir>) (--code_dir <dir> | -c <dir>) [(--freesurfer_home <dir> | -f <dir>)] [(--name <str> | -n <str>)] [--host <host>]

Options:
  -h --help                             Show this screen.
  -v --version                          Show the current version.
  -l --longitudinal                     Specify longitudinal processing. [default: False]
  -n <str> --name <str>                 Specify a name for the freesurfer processing. [default: None]
  -d <dir> --data_dir <dir>             SUBJECTS_DIR will be a sub-directory, along with an analysis directory.
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

def write_file(path, content, is_executable=False):
    with open(clean_path(path), "w") as text_file:
        text_file.write(content)
    if is_executable:
        os.chmod(path, os.stat(path).st_mode | 0111)


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
    def __init__(self, name, data_dir, code_dir, freesurfer_home, is_longitudinal=False, host=None):
        if name == None:
            self.name = "FreeSurfer"
        else:
            self.name = "FreeSurfer - "+name
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
        self.setup_dir = get_src()
        self.host = host
        if self.host == None:
            self.requires_host = False
            self.host = "$HOSTNAME"
        else:
            self.requires_host = True
        self.config_loc = self.script_dir+"config.sh"
        self.config = self.get_config()

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
        self.scripts = [Script("View", flags=["config","subject","timepoint","timepoints","type","phase"]),
                        Script("Extract", flags=["config","subjectlist"]),
                        Script("Cross_Initialize", flags=["config","subject","timepoint","inputfile"]),
                        Script("Cross_Restart", flags=["config","subject","timepoint"]),
                        Script("Cross_talRerun", flags=["config","subject","timepoint"]),
                        Script("Cross_maskRerun", flags=["config","subject","timepoint"]),
                        Script("Cross_cpRerun", flags=["config","subject","timepoint"]),
                        Script("Cross_wmRerun", flags=["config","subject","timepoint"]),
                        Script("Cross_gmRerun", flags=["config","subject","timepoint"])
                       ]
        if self.is_longitudinal:
            self.scripts.extend([Script("Base_Initialize", flags=["config","subject","timepoint"]),
                                 Script("Base_Restart", flags=["config","subject","timepoint"]),
                                 Script("Base_talRerun", flags=["config","subject","timepoint"]),
                                 Script("Base_maskRerun", flags=["config","subject","timepoint"]),
                                 Script("Base_cpRerun", flags=["config","subject","timepoint"]),
                                 Script("Base_wmRerun", flags=["config","subject","timepoint"]),
                                 Script("Base_gmRerun", flags=["config","subject","timepoint"]),
                                 Script("Long_Initialize", flags=["config","subject","timepoint"]),
                                 Script("Long_Restart", flags=["config","subject","timepoint"]),
                                 Script("Long_talRerun", flags=["config","subject","timepoint"]),
                                 Script("Long_maskRerun", flags=["config","subject","timepoint"]),
                                 Script("Long_cpRerun", flags=["config","subject","timepoint"]),
                                 Script("Long_wmRerun", flags=["config","subject","timepoint"]),
                                 Script("Long_gmRerun", flags=["config","subject","timepoint"])
                                ])


    def get_config(self):
        #Define Config file
        config_dict = {
            "freesurfer_home":self.freesurfer_home,
            "submit_dir":self.submit_dir,
            "subjects_dir":self.subjects_dir,
            "analysis_dir":self.analysis_dir,
            "monitor_dir":self.monitor_dir,
            "setup_dir":self.setup_dir,
            "log_dir":self.log_dir,
            "is_longitudinal":self.is_longitudinal,
            "host":self.host,
        }
        config = """#!/bin/bash

export SETUP_DIR={setup_dir}
export SUBMIT_DIR={submit_dir}
export FREESURER_HOME={freesurfer_home}
export SUBJECTS_DIR={subjects_dir}
export ANALYSIS_DIR={analysis_dir}
export MONITOR_DIR={monitor_dir}
export LOGS_DIR={log_dir}
export IS_LONGITUDINAL={is_longitudinal}
export DESIRED_HOSTNAME={host}""".format(**config_dict)
        return config

    def render_script(self, script):
        submit_arg_string = "LOGS_DIR=${LOGS_DIR} SUBJECTS_DIR=${SUBJECTS_DIR} SETUP_DIR=${SETUP_DIR}"
        if "subject" in script.flags:
            if self.is_longitudinal:
                submit_arg_string += " TARGET=${subject}_${timepoint}"
            else:
                submit_arg_string += " TARGET=${subject}"
        else:
            submit_arg_string += " TARGET=Project"

        script_render = """#!/bin/sh

accepted_arguments="$@"

source {config_log}
export CONFIG_FILE={config_log}
export SETUP_DIR=$SETUP_DIR
export SUBMIT_DIR=$SUBMIT_DIR
export FREESURER_HOME=$FREESURER_HOME
export SUBJECTS_DIR=$SUBJECTS_DIR
export ANALYSIS_DIR=$ANALYSIS_DIR
export MONITOR_DIR=$MONITOR_DIR
export LOGS_DIR=$LOGS_DIR
export IS_LONGITUDINAL=$IS_LONGITUDINAL
export DESIRED_HOSTNAME=$DESIRED_HOSTNAME

while [[ "$#" > 1 ]]; do case $1 in\n""".format(config_log=self.config_loc)
        for flag in script.flags:
            if flag == "subject":
                script_render += '    --{0}) {0}=$2;;\n'.format(flag)
            elif flag == "timepoint" and self.is_longitudinal and "Base" not in script.name:
                script_render += '    --{0}) {0}=$2;;\n'.format(flag)
        script_render += """    *);;
esac; shift
done
"""
        if script.name == "View":
            script_render += """
exec ${{SETUP_DIR}}/executables/{step_name}.sh $accepted_arguments
        """.format(step_name=script.name)
        else:
            script_render += """
condor_submit ${{SUBMIT_DIR}}/cs_{step_name}.txt {arg_string} args="$accepted_arguments"
        """.format(step_name=script.name, arg_string=submit_arg_string)
        return script_render

    def render_submit(self, script):
        if script.name == "Extract":
            target = "project"
        else:
            target = "subject"

        script_render = """Universe=vanilla
getenv=True
request_memory={memory}
initialdir=$(SUBJECTS_DIR)
Executable=$(SETUP_DIR)/executables/{step_name}.sh
Log=$(LOGS_DIR)/{step_name}_$(TARGET)_log.txt
Output=$(LOGS_DIR)/{step_name}_$(TARGET)_out.txt
Error=$(LOGS_DIR)/{step_name}_$(TARGET)_err.txt
arguments=$(args)
Queue""".format(memory=script.memory, step_name=script.name, target=target)
        return script_render


    def create_directories(self):
        for directory in self.dirs:
            try:
                os.makedirs(directory)
            except:
                pass

    def write_scripts(self):
        write_file(self.script_dir+"config.sh", self.get_config(), is_executable=True)
        for script in self.scripts:
            write_file(self.script_dir+script.name+".sh", self.render_script(script), is_executable=True)
            if script.name != "View":
                write_file(self.submit_dir+"cs_"+script.name+".txt", self.render_submit(script))

    def create_monitor(self):
        if exists(self.monitor_dir):
            shutil.rmtree(self.monitor_dir)
        palantir.create(self.monitor_dir, self.name)
        palantir.update(self.monitor_dir, add_rows=["Project"], add_columns=[script.name for script in self.scripts])
        for script in self.scripts:
            if script.name != "Extract":
                palantir.cell(self.monitor_dir, row_id="Project", column_id=script.name, text="N/A", background_color="#d2d2d2", text_color="#f0f0f0", boolean="False")


class Script(object):
    """
    Script class.

    """
    def __init__(self, name, flags, memory=3072):
        self.name = idify(name)
        self.flags = flags
        self.memory = memory


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

  if args["--name"] in ["None", None]:
      args["--name"] = None
  else:
      args["--name"] = str(args["--name"])

  # Setup
  project = Project(name=args["--name"], data_dir=clean_path(args["--data_dir"]), code_dir=clean_path(args["--code_dir"]), freesurfer_home=clean_path(args["--freesurfer_home"]), is_longitudinal=args["--longitudinal"], host=args["--host"])
  project.create_directories()
  project.write_scripts()
  project.create_monitor()
  print("Setup Complete!")

#------------------------------------
#    Main
#------------------------------------

if __name__ == '__main__':
    args = docopt(doc, version='Setup FreeSurfer v{0}'.format(Version))
    run(args)

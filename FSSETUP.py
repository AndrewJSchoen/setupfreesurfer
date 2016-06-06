#!/usr/bin/env python

Version = "0.1"
doc = """
Run FS SETUP.

Usage:
  FSSETUP.py [options] --input=InputFile --freesurferdir=FreeSurferDir [--monitortype=MonitorType --monitorplace=MonitorPlace]

Options:
  -h --help                                       Show this screen.
  -v --version                                    Show the current version.
  -l --longitudinal                               Specify longitudinal processing. Include a "Timepoint" column in the inputfile. [default: False]
  -i=InputFile --input=InputFile                  Input csv file. Expects a column "Subjects", as well as some data columns. [default: False]
  -f=FreeSurferDir --freesurferdir=FreeSurferDir  Folder for freesurfer. 'SUBJECTS_DIR' will be a sub-directory, along with scripts. [default: False]
  -m=MonitorType --monitortype=MonitorType        Either "None", "JobMonitor", or "Google". [default: None]
  -p=MonitorPlace --monitorplace=MonitorPlace     For "JobMonitor", a directory. For "Google", a spreadsheet key.
"""


import csv, sys, os, shutil, subprocess, math, pandas
sys.path.append("lib/docopt")
from docopt import docopt
from lib import SetupJobMonitor

#============================================================================
#============ Functions =====================================================

def exists(path):
  if os.path.exists(cleanPathString(path)):
      return(1)
  else:
      return(0)

def systemCall(command):
  p = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True)
  return p.stdout.read()

def parseCSV(csvfilepath, headerlist=[]):
  if exists(csvfilepath):
    csvfilepath = cleanPathString(csvfilepath)
    print("Parsing CSV File '{0}'.".format(csvfilepath))
    csvcontent = pandas.read_csv(csvfilepath, converters={'Subject': lambda x: str(x)})
    csvcontent.index = csvcontent["Subject"]
    csvcontent.drop("Subject", axis=1, inplace=True)
    if "Include" in list(csvcontent.columns.values):
        headerlist.append("Include")
    if "Timepoint" in list(csvcontent.columns.values):
        headerlist.append("Timepoint")
    for columnid in list(csvcontent.columns.values):
        if "File" in columnid:
            headerlist.append(columnid)
    filecolumnexists = False
    for columnid in headerlist:
        if "File" in columnid:
            filecolumnexists = True
    if not filecolumnexists:
        print("Your inputfile did not include a file column. Exiting now.")
        sys.exit(1)
    if len(headerlist) > 0:
        csvcontent=csvcontent[headerlist]
    return csvcontent
  else:
      print("CSV File '{0}' does not exist! Exiting now.".format(csvfilepath))
      sys.exit(1)

def writeFile(text, filename):
  #Write to a file
  with open(filename, 'w') as writefile:
      writefile.write(text)

def cleanPathString(path):
  if path.endswith("/"):
    path = path[:-1]
  if path.startswith("="):
    path = path[1:]
  realpath = os.path.realpath(path)
  return realpath

def cleanString(string):
  if string.startswith("="):
    string = string[1:]
  return string

def trimCSV(csv, headers):
  newCSV = csv[headers]
  return newCSV

def removeRowsWithCriteria(csv, column, value):
  print("Revmoving cases where {0} = {1}".format(column, value))
  csv = csv[csv[column] != value]
  return csv

def cleanargs(args):
    arguments = {}
    if args["--longitudinal"] == False or args["--longitudinal"] == "False":
        arguments["IsLongitudinal"] = False
    else:
        arguments["IsLongitudinal"] = True

    if cleanString(args["--monitortype"]) == "None":
        arguments["MonitorType"] = "None"
    elif cleanString(args["--monitortype"]) == "Google":
        arguments["MonitorType"] = "Google"
        if args["--monitorplace"] != None:
            arguments["SpreadsheetKey"] = cleanString(args["--monitorplace"])
        else:
            print("Error: You failed to specify a spreadsheet key with the --monitorplace flag. Exiting.")
            sys.exit(1)
    elif cleanString(args["--monitortype"]) == "JobMonitor":
        arguments["MonitorType"] = "JobMonitor"
        if args["--monitorplace"] != None:
            arguments["MonitorDir"] = cleanPathString(args["--monitorplace"])
        else:
            print("Error: You failed to specify a monitor directory with the --monitorplace flag. Exiting.")
            sys.exit(1)
    else:
        print("Error: You failed to specify a valid monitor type with the --monitortype flag ({0}). Exiting.".format(cleanString(args["--monitortype"])))
        sys.exit(1)

    arguments["FreeSurferDir"] = cleanPathString(args["--freesurferdir"])
    arguments["ThisDir"] = os.path.abspath(os.path.join(os.path.dirname( __file__ )))

    arguments["InputFile"] = parseCSV(args["--input"])
    if "Subject" != arguments["InputFile"].index.name:
        print("Your inputfile did not include 'Subject' as a column in the inputfile. Exiting now.")
        print(arguments["InputFile"])
        sys.exit(1)
    if "Timepoint" not in arguments["InputFile"].columns.values and arguments["IsLongitudinal"]:
        print("You specified longitudinal structure, but did not include 'Timepoint' as a column in the inputfile. Exiting now.")
        sys.exit(1)
    elif "Timepoint" in arguments["InputFile"].columns.values and arguments["IsLongitudinal"] == False:
        print("Warning: Your inputfile includes 'Timepoint' as a column in the inputfile, but you did not specify longitudinal processing. Proceeding without timepoint information.")
        relevantheaders=list(arguments["InputFile"].columns.values)
        relevantheaders.remove("Timepoint")
        arguments["InputFile"] = trimCSV(arguments["InputFile"], relevantheaders)

    if "Include" in list(arguments["InputFile"].columns.values):
      relevantheaders=list(arguments["InputFile"].columns.values)
      arguments["InputFile"] = removeRowsWithCriteria(arguments["InputFile"], "Include", "N")
      relevantheaders.remove("Include")
      arguments["InputFile"] = trimCSV(arguments["InputFile"], relevantheaders)

    print(arguments["InputFile"])

    return arguments


#============================================================================
#============ String Library ================================================

def defineScripts(arguments):
    ScriptHeader = """#!/bin/sh

export FREESURFER_HOME=/apps/x86_64_sci7/freesurfer-latest
source $FREESURFER_HOME/SetUpFreeSurfer.sh
export SUBJECTS_DIR={0}/subjects

STARTTIME=$(date +%s)
curtime=$(date +%FT%R:%S)
""".format(arguments["FreeSurferDir"])
    if arguments["IsLongitudinal"]:
        substring = "${subid}_${time}"
        subarglist = ["subid=$1", "time=$2"]
        allotherargs = "${@:3}"
        allbutfirstarg = "${@:2}"
    else:
        substring = "${subid}"
        subarglist = ["subid=$1"]
        allotherargs = "${@:2}"
        allbutfirstarg = allotherargs

    orig =      {"Name": "Orig",
                 "InputLines": subarglist + ["inputstring=''", 'for i in {0} ; do inputstring="${{inputstring}} -i ${{i}}" ; done'.format(allotherargs)],
                 "Steps": ["recon-all ${{inputstring}} -subjid {0} -all".format(substring)]}
    restart =   {"Name": "Restart",
                 "InputLines": subarglist,
                 "Steps": ["recon-all -clean -subjid {0} -all".format(substring)]}
    base_gen =  {"Name": "Base",
                 "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                 "Steps": ["recon-all -base ${subid}_base ${inputstring} -all"]}
    long_gen =  {"Name": "Long",
                 "InputLines": subarglist,
                 "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -all"]}


    cross_talEdit =   {"Name": "Cross_talEdit",
                       "InputLines": subarglist,
                       "Steps": ["recon-all -subjid {0} -all".format(substring)]}

    cross_maskEdit = {"Name": "Cross_maskEdit",
                         "InputLines": subarglist,
                         "Steps": ["recon-all -autorecon2 -autorecon3 -subjid {0}".format(substring)]}
    cross_cpEdit =   {"Name": "Cross_cpEdit",
                         "InputLines": subarglist,
                         "Steps": ["recon-all -autorecon2-cp -autorecon3 -subjid {0}".format(substring)]}
    cross_wmEdit =   {"Name": "Cross_wmEdit",
                         "InputLines": subarglist,
                         "Steps": ["recon-all -autorecon2-wm -autorecon3 -subjid {0}".format(substring)]}
    cross_gmEdit =   {"Name": "Cross_gmEdit",
                         "InputLines": subarglist,
                         "Steps": ["recon-all -autorecon-pial -subjid {0} -all".format(substring)]}

    base_talEdit = {"Name": "Base_talEdit",
                        "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                        "Steps": ["recon-all -base ${subid}_base ${inputstring} -all"]}

    base_maskEdit = {"Name": "Base_maskEdit",
                        "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                        "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2 -autorecon3"]}
    base_cpEdit =   {"Name": "Base_cpEdit",
                        "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                        "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2-cp -autorecon3"]}
    base_wmEdit =   {"Name": "Base_wmEdit",
                        "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                        "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon2-wm -autorecon3"]}
    base_gmEdit =   {"Name": "Base_gmEdit",
                        "InputLines": ["subid=$1", "inputstring=''", "inputlist=''", 'for t in {0} ; do inputstring="${{inputstring}} -tp ${{subid}}_${{t}}" ; inputlist="${{inputlist}} ${{subid}}_${{t}} ; done'.format(allbutfirstarg)],
                        "Steps": ["recon-all -base ${subid}_base ${inputstring} -autorecon-pial"]}

    long_talEdit = {"Name": "Long_talEdit",
                        "InputLines": subarglist,
                        "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -all"]}
    long_maskEdit = {"Name": "Long_maskEdit",
                        "InputLines": subarglist,
                        "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2 -autorecon3"]}
    long_cpEdit =   {"Name": "Long_cpEdit",
                        "InputLines": subarglist,
                        "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2-cp -autorecon3"]}
    long_wmEdit =   {"Name": "Long_wmEdit",
                        "InputLines": subarglist,
                        "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon2-wm -autorecon3"]}
    long_gmEdit =   {"Name": "Long_gmEdit",
                        "InputLines": subarglist,
                        "Steps": ["recon-all -long ${subid}_${time} ${subid}_base -autorecon-pial"]}

    extractvals = {"Name": "ExtractVals",
                   "InputLines": ["subjectslist=$@"],
                   "Steps": ["aparcstats2table --hemi lh --subjects $subjectslist --meas area --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-area-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi lh --subjects $subjectslist --meas meancurv --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-meancurv-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi lh --subjects $subjectslist --meas thickness --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-thickness-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi lh --subjects $subjectslist --meas volume --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/lh_aparc-a2009-volume-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi rh --subjects $subjectslist --meas area --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-area-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi rh --subjects $subjectslist --meas meancurv --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-meancurv-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi rh --subjects $subjectslist --meas thickness --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-thickness-table.csv".format(arguments["FreeSurferDir"]),
                             "aparcstats2table --hemi rh --subjects $subjectslist --meas volume --parc aparc.a2009s --tablefile {0}/analysis/atlas-extracted/rh_aparc-a2009-volume-table.csv".format(arguments["FreeSurferDir"]),
                             "segstats2table --subjects $subjectslist --stats aseg.stats --tablefile {0}/analysis/atlas-extracted/aseg-vol-table.csv".format(arguments["FreeSurferDir"])]}


    cross_talView = {"Name": "Cross_talView",
                     "InputLines": subarglist,
                     "Steps": ["tkregister2 --mgz --s {0} --fstal --surf orig".format(substring)]}

    cross_maskView = {"Name": "Cross_maskView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"], substring)]}

    cross_cpView = {"Name": "Cross_cpView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz {0}/subjects/{1}/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/{1}/surf/lh.white:edgecolor=yellow {0}/subjects/{1}/surf/lh.pial:edgecolor=red {0}/subjects/{1}/surf/rh.white:edgecolor=yellow {0}/subjects/{1}/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}

    cross_wmView = {"Name": "Cross_wmView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz {0}/subjects/{1}/mri/wm.mgz:opacity=0.5 -f {0}/subjects/{1}/surf/lh.white:edgecolor=yellow {0}/subjects/{1}/surf/lh.pial:edgecolor=red {0}/subjects/{1}/surf/rh.white:edgecolor=yellow {0}/subjects/{1}/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}

    cross_gmView = {"Name": "Cross_gmView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}/mri/T1.mgz {0}/subjects/{1}/mri/brainmask.mgz {0}/subjects/{1}/mri/wm.mgz:opacity=0 -f {0}/subjects/{1}/surf/lh.white:edgecolor=yellow {0}/subjects/{1}/surf/lh.pial:edgecolor=red {0}/subjects/{1}/surf/rh.white:edgecolor=yellow {0}/subjects/{1}/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}


    base_talView = {"Name": "Base_talView",
                     "InputLines": ["subid=$1"],
                     "Steps": ["tkregister2 --mgz --s ${subid}_base --fstal --surf orig"]}

    base_maskView = {"Name": "Base_maskView",
                     "InputLines": ["subid=$1"],
                     "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"])]}

    base_cpView = {"Name": "Base_cpView",
                     "InputLines": ["subid=$1"],
                     "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}

    base_wmView = {"Name": "Base_wmView",
                   "InputLines": ["subid=$1"],
                   "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:opacity=0.5 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}

    base_gmView = {"Name": "Base_gmView",
                   "InputLines": ["subid=$1"],
                   "Steps": ["freeview -v {0}/subjects/${{subid}}_base/mri/T1.mgz {0}/subjects/${{subid}}_base/mri/brainmask.mgz {0}/subjects/${{subid}}_base/mri/wm.mgz:opacity=0 -f {0}/subjects/${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"])]}


    long_talView = {"Name": "Long_talView",
                    "InputLines": subarglist,
                    "Steps": ["tkregister2 --mgz --s {0}.long.${{subid}}_base --fstal --surf orig".format(substring)]}

    long_maskView = {"Name": "Long_maskView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz:colormap=heat:opacity=0.4".format(arguments["FreeSurferDir"], substring)]}

    long_cpView = {"Name": "Long_cpView",
                     "InputLines": subarglist,
                     "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:colormap=heat:opacity=0.3 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}

    long_wmView = {"Name": "Long_wmView",
                   "InputLines": subarglist,
                   "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:opacity=0.5 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}

    long_gmView = {"Name": "Long_gmView",
                   "InputLines": subarglist,
                   "Steps": ["freeview -v {0}/subjects/{1}.long.${{subid}}_base/mri/T1.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/brainmask.mgz {0}/subjects/{1}.long.${{subid}}_base/mri/wm.mgz:opacity=0 -f {0}/subjects/{1}.long.${{subid}}_base/surf/lh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/lh.pial:edgecolor=red {0}/subjects/{1}.long.${{subid}}_base/surf/rh.white:edgecolor=yellow {0}/subjects/{1}.long.${{subid}}_base/surf/rh.pial:edgecolor=red".format(arguments["FreeSurferDir"], substring)]}

    if arguments["IsLongitudinal"]:
        ScriptList = [orig, restart, base_gen, long_gen, cross_talEdit, cross_maskEdit, cross_cpEdit, cross_wmEdit, cross_gmEdit, base_talEdit, base_maskEdit, base_cpEdit, base_wmEdit, base_gmEdit, long_talEdit, long_maskEdit, long_cpEdit, long_wmEdit, long_gmEdit, extractvals, cross_talView, cross_maskView, cross_cpView, cross_wmView, cross_gmView, base_talView, base_maskView, base_cpView, base_wmView, base_gmView, long_talView, long_maskView, long_cpView, long_wmView, long_gmView]
    else:
        ScriptList = [orig, restart, cross_talEdit, cross_maskEdit, cross_cpEdit, cross_wmEdit, cross_gmEdit, extractvals, cross_talView, cross_maskView, cross_cpView, cross_wmView, cross_gmView]

    return ScriptHeader, ScriptList

#============================================================================
#============ Script Writing ================================================

def writeScript(header, script, index, arguments):
    scriptlist = [header]
    for inputline in script["InputLines"]:
        scriptlist.append(inputline)
    scriptlist.extend(["STARTTIME=$(date +%s)", "CURRENTTIME=$(date +%FT%R:%S)"])
    for step in script["Steps"]:
        if arguments["MonitorType"] != None:
            if arguments["MonitorType"] == "Google":
                if script["Name"] == "ExtractVals":
                    update = "{0}/lib/writeToSpreadsheet.py Project {1} {{0}}-{3} {2}".format(arguments["ThisDir"], index, arguments["SpreadsheetKey"], "${{CURRENTTIME}}")
                elif "Base" in script["Name"]:
                    update = "for i in $inputlist ; do {0}/lib/writeToSpreadsheet.py {3} {1} {{0}}-{4} {2} ; done".format(arguments["ThisDir"], index, arguments["SpreadsheetKey"], "${{i}}", "${{CURRENTTIME}}")
                elif arguments["IsLongitudinal"]:
                    update = "{0}/lib/writeToSpreadsheet.py {3}_{4} {1} {{0}}-{5} {2}".format(arguments["ThisDir"], index, arguments["SpreadsheetKey"], "${{subid}}", "${{time}}", "${{CURRENTTIME}}")
                else:
                    update = "{0}/lib/writeToSpreadsheet.py {3} {1} {{0}}-{4} {2}".format(arguments["ThisDir"], index, arguments["SpreadsheetKey"], "${{subid}}", "${{CURRENTTIME}}")
                wrappedsteps = [update.format("Running"), "if {0}; then".format(step), "CURRENTTIME=$(date +%FT%R:%S)", update.format("Finished"), "else", "CURRENTTIME=$(date +%FT%R:%S)", update.format("Error"), "exit", "fi"]
            else:
                if script["Name"] == "ExtractVals":
                    update = "{0}/statusupdate.py Project {1} {{0}}".format(arguments["MonitorDir"], script["Name"])
                elif "Base" in script["Name"]:
                    update = "for i in $inputlist ; do {0}/statusupdate.py {2} {1} {{0}} ; done".format(arguments["MonitorDir"], script["Name"], "${{i}}")
                elif arguments["IsLongitudinal"]:
                    update = "{0}/statusupdate.py {2}_{3} {1} {{0}}".format(arguments["MonitorDir"], script["Name"], "${{subid}}", "${{time}}")
                else:
                    update = "{0}/statusupdate.py {2} {1} {{0}}".format(arguments["MonitorDir"], script["Name"], "${{subid}}")
                wrappedsteps = [update.format("Running"), "if {0}; then".format(step), update.format("Finished"), "else", update.format("Error"), "exit", "fi"]

            scriptlist.extend(wrappedsteps)
        else:
            scriptlist.append(step)
    scriptlist.extend(["ENDTIME=$(date +%s)", "TOTALSEC=$((ENDTIME - STARTTIME))", "echo {0} took $TOTALSEC seconds".format(script["Name"])])
    scriptcontents="\n".join(scriptlist)
    writeFile(scriptcontents, arguments["FreeSurferDir"]+"/scripts/"+script["Name"]+".sh")
    os.chmod(arguments["FreeSurferDir"]+"/scripts/"+script["Name"]+".sh", os.stat(arguments["FreeSurferDir"]+"/scripts/"+script["Name"]+".sh").st_mode | 0111)

#============================================================================
#============ Submit Writing ================================================

def writeSubmit(script, arguments):
    print(script["Name"])
    standardheader = """Universe=vanilla
getenv=True
request_memory=3072
initialdir={0}/subjects
Executable={0}/scripts/{1}.sh
Log={0}/scripts/condorlogs/{1}_$(target)_log.txt
Output={0}/scripts/condorlogs/{1}_$(target)_out.txt
Error={0}/scripts/condorlogs/{1}_$(target)_err.txt
Notification=Error
""".format(arguments["FreeSurferDir"], script["Name"])
    if script["Name"] == "ExtractVals":
        subjectlist = []
        if arguments["IsLongitudinal"]:
            for rowindex, row in arguments["InputFile"].iterrows():
                subjectlist.append("{0}_{1}".format(rowindex, row["Timepoint"]))
        else:
            for rowindex, row in arguments["InputFile"].iterrows():
                subjectlist.append("{0}".format(rowindex))
        queuelist = ["\ntarget=Project\narguments=" + '"' + " ".join(subjectlist) + '"' + "\nQueue\n"]
    elif script["Name"] == "Orig":
        queuelist = []
        for rowindex, row in arguments["InputFile"].iterrows():
            filesheaders = []
            subjexistingfiles = []
            rowindices = list(row.index)
            for key in rowindices:
                if "File" in key:
                    filesheaders.append(key)
            for fileheader in filesheaders:
                if row[fileheader] != None:
                    subjexistingfiles.append(row[fileheader])
            subjarguments = [rowindex]
            if arguments["IsLongitudinal"]:
                subjarguments.append(str(row["Timepoint"]))
            subjarguments.extend(subjexistingfiles)
            if arguments["IsLongitudinal"]:
                queuelist.append('\ntarget={0}_{1}\narguments="{2}"\nQueue\n'.format(rowindex, row["Timepoint"], " ".join(subjarguments)))
            else:
                queuelist.append('\ntarget={0}\narguments="{1}"\nQueue\n'.format(rowindex, " ".join(subjarguments)))
    elif script["Name"] in ["Restart", "Cross_talEdit", "Cross_maskEdit", "Cross_cpEdit", "Cross_wmEdit", "Cross_gmEdit", "Long", "Long_talEdit", "Long_maskEdit", "Long_cpEdit", "Long_wmEdit", "Long_gmEdit"]:
        queuelist = []
        for rowindex, row in arguments["InputFile"].iterrows():
            if arguments["IsLongitudinal"]:
                queuelist.append('\ntarget={0}_{1}\narguments="{0} {1}"\nQueue\n'.format(rowindex, row["Timepoint"]))
            else:
                queuelist.append('\ntarget={0}\narguments="{0}"\nQueue\n'.format(rowindex))
    else:
        queuelist = []
        uniquesubjects = set(list(arguments["InputFile"].index))
        for uniquesubject in uniquesubjects:
            subjectframesubsection = arguments["InputFile"][(arguments["InputFile"].index == str(uniquesubject))]
            intsubjecttimepoints = list(subjectframesubsection["Timepoint"])
            subjecttimepoints = []
            for subjecttimepoint in intsubjecttimepoints:
                subjecttimepoints.append(str(subjecttimepoint))
            subjarguments = [uniquesubject] + subjecttimepoints
            queuelist.append("\ntarget="+uniquesubject+"\narguments=" + '"' + " ".join(subjarguments) + '"' + "\nQueue\n")
    condorsubmitlist = [standardheader] + queuelist
    condorsubmitcontents = "\n".join(condorsubmitlist)
    writeFile(condorsubmitcontents, arguments["FreeSurferDir"]+"/scripts/condorsubmit/cs_"+script["Name"]+".txt")


#============================================================================
#============ Main ==========================================================

def run(args):

  # 1: Argument Parsing
  protoarguments = docopt(doc, argv=args, version='Run FS SETUP v{0}'.format(Version))
  arguments = cleanargs(protoarguments)

  #Make the subject directory.
  dirs = [arguments["FreeSurferDir"], arguments["FreeSurferDir"]+"/subjects", arguments["FreeSurferDir"]+"/analysis", arguments["FreeSurferDir"]+"/analysis/atlas-extracted", arguments["FreeSurferDir"]+"/scripts", arguments["FreeSurferDir"]+"/scripts/condorsubmit", arguments["FreeSurferDir"]+"/scripts/condorlogs"]
  for directory in dirs:
      if not exists(directory):
        os.mkdir(directory)

  ScriptHeader, ScriptList = defineScripts(arguments)

  for scriptindex, script in enumerate(ScriptList):
      writeScript(ScriptHeader, script, scriptindex, arguments)
      if "View" not in script["Name"]:
          writeSubmit(script, arguments)

  if arguments["MonitorType"] == "JobMonitor":
      jobsObj = [{"ID":"Project", "NAME":"Project"}]
      if arguments["IsLongitudinal"]:
          for index, row in arguments["InputFile"].iterrows():
            jobsObj.append({"ID":index+"_"+str(row["Timepoint"]), "NAME":index+"_"+str(row["Timepoint"])})
      else:
          for index, row in arguments["InputFile"].iterrows():
            jobsObj.append({"ID":index, "NAME":index})

      eventsObj = []
      for script in ScriptList:
        scriptDict = {"ID": script["Name"], "NAME": script["Name"]}
        if scriptDict not in eventsObj:
          eventsObj.append(scriptDict)

      SetupJobMonitor.create({"processName": "FreeSurfer | Live Updates", "monitorDir": arguments["MonitorDir"], "jobs": jobsObj, "events": eventsObj})
  elif arguments["MonitorType"] == "Google":
      listdict = []
      columncount=len(ScriptList)
      columns = []
      if arguments["IsLongitudinal"]:
          columns.append("Timepoint")
      for script in ScriptList:
          columns.append(script["Name"])
      for rowindex, rowcontents in arguments["InputFile"].iterrows():
          if arguments["IsLongitudinal"]:
              listdict.append((rowindex, [rowcontents["Timepoint"]] + ["Inactive"] * columncount))
          else:
              listdict.append((rowindex, ["Inactive"] * columncount))
      writecsv = pandas.DataFrame.from_items(listdict,orient='index', columns=columns)
      writecsv.to_csv(arguments["FreeSurferDir"]+"/googlemonitor.csv", index=False)

#============================================================================
#============ Entry =========================================================

if __name__ == '__main__':
    args = sys.argv
    del args[0]
    run(args)

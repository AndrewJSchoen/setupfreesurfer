Setup FreeSurfer
============
A standardized way of creating a FreeSurfer Project.
---------------------

FreeSurfer is fairly easy to initiate, but there are lots of different types of edits that can be done within the pipeline, and no out-of-the-box way of tracking them. Setup FreeSurfer attempts to standardize all these things, creating standard scripts for running reprocessing commands, viewing commands, and tracking with a web-based spreadsheet.

Options:
Running the script with the `-h` option will output a help page, which lists the information below.
Usage:
`setupfreesurfer.py [options] (--data_dir <dir> | -d <dir>) (--code_dir <dir> | -c <dir>) [(--freesurfer_home <dir> | -f <dir>)] [--host <host>]`

Breaking this down, you must provide a data and code directory (if it does not exist it will be created), Additionally, there are options to indicate the `--freesurfer_home` (omitting will try to use an environmental variable), and host. If you specify `--host` as `current`, the current host is required. The `-l` command creates scripts for the longitudinal stream.

##Requirements:
* Python 2.7
* [FreeSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/FreeSurferWiki)

### License ###
MIT

### Links ###
 - [git](https://github.com/AndrewJSchoen)
 - [git-repo-url](https://github.com/AndrewJSchoen/setupfreesurfer.git)

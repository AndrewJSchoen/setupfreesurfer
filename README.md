Dash
============
A simple, locally-running dashboard you can update via the command-line.
---------------------

### Usage ###
Execution is fairly simple:

```
# Create a dashboard
dash.py create <dir> (-n <text> | --name <text>)
# Update a dashboard's structure
dash.py update <dir> [--addrow <row>...] [--rmrow <row>...] [--addcol <col>...] [--rmcol <col>...]
# Update a cell in the dashboard
dash.py cell <dir> (-r <row> | --row <row>) (-c <col> | --col <col>) [options]
```
Note! You can also import dash as a module and use the create, update, and cell functions!

Structural Updates
  - Add columns, rows
  - Remove columns, rows

Cell Features
  - Text
  - Color
  - Background-Color
  - Animation
  - Boolean
  - Images
  - Notes

### Version ###
0.1.3

### Upcoming

 - Write Tests
 - Query ability
 - Shiftable columns/rows
 - Renaming column/row text

### License ###
MIT

### Links ###
 - [git](https://github.com/AndrewJSchoen)
 - [git-repo-url](https://github.com/AndrewJSchoen/dash.git)

Thanks!
 - [docopt](https://github.com/docopt/docopt)
 - [bootstrap](https://github.com/twbs/bootstrap)
 - [jTemplates](http://jtemplates.tpython.com)

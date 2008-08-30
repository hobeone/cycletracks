#!/bin/bash
for i in `svn st --ignore-externals | egrep -v '^X' | awk '{print $2}'` ; do tkdiff $i; done

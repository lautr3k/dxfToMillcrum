#!/usr/bin/python

#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2010 Dan Falck <ddfalck@gmail.com>                      *
#*   derived from Yorik van Havre's <yorik@gmx.fr>  importDXF.py           *
#*   script that is part of the Draft plugin for FreeCAD                   *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU General Public License (GPL)            *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************
#*                                                                         *
#*   This script uses a DXF-parsing library created by Stani,              *
#*   Kitsu and Migius for Blender                                          *
#*                                                                         *
#*   It is also based off the Heeks DXF importer                           *
#*                                                                         *
#***************************************************************************

import sys
sys.path.append('./lib')
from dxfReader import readDXF

# -----------------------------------------------------------------------------

# app configuration
app_name    = 'dxf2Millcrum'
app_version = '1.0.0'

# default i/o
input  = None
output = 'stdout'

# -----------------------------------------------------------------------------

# global min/max position
minX = None
maxX = None
minY = None
maxY = None

def isBiggerThan(var1, var2):
    return cmp(var1, var2) == 1

def minMaxPos(x, y):
    global minX, maxX, minY, maxY
    minX = minX if minX else x
    maxX = maxX if maxX else x
    minY = minY if minY else y
    maxY = maxY if maxY else y
    
    minX = minX if isBiggerThan(x, minX) else x
    maxX = maxX if isBiggerThan(maxX, x) else x
    minY = minY if isBiggerThan(y, minY) else y
    maxY = maxY if isBiggerThan(maxY, y) else y

# -----------------------------------------------------------------------------

def mcPolygon(polyline):
    buffer = '// '+polyline.name+'\n'
    buffer+= 'var '+polyline.name+' = {type: \'polygon\',name:\''+polyline.name+'\',points:['
    for point in polyline.points:
        buffer+= '['+str(point[0])+','+str(point[1])+'],';
    buffer = buffer.rstrip(',')
    buffer+= ']};'
    buffer+= '\nmc.cut(\'centerOnPath\','+polyline.name+', 4, [0,0]);\n'
    return buffer

# -----------------------------------------------------------------------------

class Polyline:
    uid = 1
    def __init__(self, points, startPos = 0):
        self.name   = 'polyline'+str(Polyline.uid)
        self.points = []
        if startPos > 0:
            self.points.extend(points[startPos:len(points)])
            self.points.extend(points[0:startPos])
        else:
            self.points = points
        Polyline.uid+= 1

def process_lines(lines):
    polylines = []
    last_line = []
    points    = []

    minX = 0
    minP = 0
    pos  = 0
    
    for line in lines:
        # discontinued line
        if len(last_line) and line.points[0] != last_line[1]:
            polylines.append(Polyline(points, minP))
            points = []

        # append polyline point
        points.append([line.points[0][0], line.points[0][1]])

        # calculate min x for stating point
        # from millcrum comment :  drawn to it in a CCW direction
        if pos == 0:
            minX = line.points[0][0]
        elif (isBiggerThan(minX, line.points[0][0])):
            minX = line.points[0][0]
            minP = pos
        minMaxPos(line.points[0][0], line.points[0][1])
        pos += 1

        # backup last line points
        last_line = line.points

    # add first or last polyline and return
    if len(points):
        polylines.append(Polyline(points, minP))
        return polylines

    return None

def process_polylines(lines):
    polylines = []
    points    = []
    
    for line in lines:
        points = []
        
        minX = 0
        minP = 0
        pos  = 0
        
        for linePoint in line.points:
            # append polyline point
            points.append([linePoint[0], linePoint[1]])

            # calculate min x for stating point
            if pos == 0:
                minX = linePoint[0]
            elif (isBiggerThan(minX, linePoint[0])):
                minX = linePoint[0]
                minP = pos
            minMaxPos(linePoint[0], linePoint[1])
            pos += 1

        # append polyline object
        if len(points):
            polylines.append(Polyline(points, minP))
    
    # return
    if len(polylines):
        return polylines

    return None

# -----------------------------------------------------------------------------

def process_arcs(arcs):
    print arcs

# -----------------------------------------------------------------------------

# do the main job
def process(input, output):
    # read the DXF file
    drawing = readDXF(input)

    # millcrum contents buffer
    mcBuffer = ''

    # process LINE
    lines     = drawing.entities.get_type('line')
    polylines = process_lines(lines)
    
    if polylines:
        for polyline in polylines:
            mcBuffer+= mcPolygon(polyline)

    # process POLYLINE
    polylines = drawing.entities.get_type("polyline")
    polylines.extend(drawing.entities.get_type("lwpolyline"))
    polylines = process_polylines(polylines)

    if polylines:
        for polyline in polylines:
            mcBuffer+= mcPolygon(polyline)

    # process ARC
    arcs = drawing.entities.get_type('arc')
    arcs = process_arcs(arcs)

    # surface size
    width  = (maxX if maxX else 100) + 10
    height = (maxY if maxY else 100) + 10

    # millcrum header
    buffer = 'var mc = new Millcrum({units:\'mm\',diameter:3,passDepth:1,step:1,rapid:2000,plunge:100,cut:600,zClearance:5,returnHome:true});\n\n'
    buffer+= 'mc.surface('+str(width)+','+str(height)+');\n\n'

    # millcrum contents
    buffer+= mcBuffer

    # millcrum footer
    buffer+= 'mc.get();\n'

    # output message
    if mcBuffer == '':
        print 'Sorry, nothing to display...'
    if output == 'stdout':
        print buffer
    else:
        print 'input  :', input
        print 'output :', output
        # write to output file
        f = open(output, 'w')
        f.write(buffer+'\n')
        f.close()

# -----------------------------------------------------------------------------

# user set i/o
if len(sys.argv) > 1:
    input = sys.argv[1]
if len(sys.argv) > 2:
    output = sys.argv[2]

# front controller
if input != None:
    process(input, output)
else:
    print 'USAGE: '+app_name+' input.dxf output.millcrum\n'
    print 'If an output file is not specified the Millcrum code will be output to STDOUT\n'

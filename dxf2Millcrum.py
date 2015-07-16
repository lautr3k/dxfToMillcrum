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

import sys, math
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


def is_close(n1 ,n2, limit = 0.0000000001):
    return abs(n1 - n2) < limit

# -----------------------------------------------------------------------------

def mcPolygon(polyline):
    buffer = '// '+polyline.name+'\n'
    buffer+= 'var '+polyline.name+' = {type: \'polygon\',name:\''+polyline.name+'\',points:['
    for point in polyline.points:
        buffer+= '['+str(point[0])+','+str(point[1])+'],'
    buffer = buffer.rstrip(',')
    buffer+= ']};\n'
    buffer+= 'mc.cut(\'centerOnPath\','+polyline.name+', 4, [0,0]);\n'
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

        for point in line.points:
            # append polyline point
            points.append([point[0], point[1], point[2]])

            # calculate min x for stating point
            if pos == 0:
                minX = point[0]
            elif (isBiggerThan(minX, point[0])):
                minX = point[0]
                minP = pos
            minMaxPos(point[0], point[1])
            pos += 1

        # append polyline object
        if len(points):
            polylines.append(Polyline(points, minP))
    
    # return
    if len(polylines):
        return polylines

    return None

class Arc:
    uid = 1
    def __init__(self, arc, start, end):
        self.name     = 'arc'+str(Arc.uid)
        self.radius   = arc.radius
        self.startDeg = arc.start_angle
        self.endDeg   = arc.end_angle
        self.startPos = start
        self.endPos   = end
        self.points   = []
        Arc.uid+= 1

        points = []
        angles = abs(arc.end_angle - arc.start_angle)

        minX = 0
        minP = 0
        pos  = 0

        for angle in range(int(angles)+1):
            a = arc.start_angle + angle
            x = math.cos(math.radians(a))
            y = math.sin(math.radians(a))
            
            # round to zero if is close enough
            x = 0 if is_close(x, 0) else x
            y = 0 if is_close(y, 0) else y

            # real position
            x = (x * arc.radius) + arc.loc[0]
            y = (y * arc.radius) + arc.loc[1]

            # calculate min x for stating point
            if pos == 0:
                minX = x
            elif (isBiggerThan(minX, x)):
                minX = x
                minP = pos
            minMaxPos(x, y)
            pos += 1

            # position
            points.append([x, y])

        # add last point
        #points.append(end)

        if minP > 0:
            self.points.extend(points[minP:len(points)])
            self.points.extend(points[0:minP])
        else:
            self.points = points

def process_arcs(arcs):
    mcArcs = []
    for arc in arcs:
        x1 = math.cos(math.radians(arc.start_angle))
        y1 = math.sin(math.radians(arc.start_angle))
        x2 = math.cos(math.radians(arc.end_angle))
        y2 = math.sin(math.radians(arc.end_angle))
        
        # round to zero if is close enough
        x1 = 0 if is_close(x1, 0) else x1
        y1 = 0 if is_close(y1, 0) else y1
        x2 = 0 if is_close(x2, 0) else x2
        y2 = 0 if is_close(y2, 0) else y2
        
        v1 = [(x1 * arc.radius) + arc.loc[0], (y1 * arc.radius) + arc.loc[1]]
        v2 = [(x2 * arc.radius) + arc.loc[0], (y2 * arc.radius) + arc.loc[1]]

        mcArcs.append(Arc(arc, v1, v2))

    # return
    if len(mcArcs):
        return mcArcs

    return None

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

    # process ARCS
    arcs = drawing.entities.get_type('arc')
    arcs = process_arcs(arcs)
    
    if arcs:
        for arc in arcs:
            mcBuffer+= mcPolygon(arc)

    # surface size
    width  = (maxX if maxX else 100) + 10
    height = (maxY if maxY else 100) + 10

    # millcrum header
    buffer = 'var mc = new Millcrum({units:\'mm\',diameter:3,passDepth:1,step:1,rapid:2000,plunge:100,cut:600,zClearance:5,returnHome:true});\n\n'
    buffer+= 'mc.surface('+str(width)+','+str(height)+');\n\n'

    # millcrum contents
    buffer+= mcBuffer + '\n'

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

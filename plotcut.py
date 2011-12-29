#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import codecs
import logging
import numpy

from optparse import OptionParser

from collections import deque
from mako.template import Template
from BeautifulSoup import BeautifulStoneSoup



log = logging.getLogger('plotcutsvg')



def decode_transform(t):
    trans = re.compile('translate\(([0-9.e-]+),([0-9.e-]+)\)')
    matr = re.compile('matrix\(([0-9.e-]+),([0-9.e-]+),([0-9.e-]+),([0-9.e-]+),([0-9.e-]+),([0-9.e-]+)\)')
    if trans.match(t):
        x = trans.sub('\\1', t)
        y = trans.sub('\\2', t)
        x = float(x)
        y = float(y)
        t = numpy.matrix('1.0, 0.0, %s; 0.0, 1.0, %s; 0.0, 0.0, 1.0' % (x, y))
    elif matr.match(t):
        a = float(matr.sub('\\1', t))
        b = float(matr.sub('\\2', t))
        c = float(matr.sub('\\3', t))
        d = float(matr.sub('\\4', t))
        e = float(matr.sub('\\5', t))
        f = float(matr.sub('\\6', t))
        t = numpy.matrix([[a, c, e], [b, d, f], [0., 0., 1.]])
    else:
        raise Exception, t
#    log.debug(t)
    return t

def magnitude(v):
    return numpy.linalg.norm(v, ord=1)
    
def distance(p1, p2):
    return magnitude(p2 - p1)
    

def absolute_paths_to_plotcut_svg(paths):

    svg_template = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg>

%for path in paths:
<path
d="
%for command, coords in path:
${command}
%for coord in coords:
${coord[0,0]},${coord[1,0]}
%endfor
%endfor
"
style="fill:none;stroke:#000000;stroke-width:0.03mm;" />
%endfor

</svg>
"""
    return Template(svg_template).render(paths=paths)




def split_paths(d, transform, point):
    minimum_distance = .1;

    instruction_options = {
        'C':6,
        'c':6,
        'H':1,
        'h':1,
        'L':2,
        'l':2,
        'M':2,
        'm':2,
        'V':1,
        'v':1,
        'Z':0,
        'z':0,
        }
    instruction_list = []
    parts = re.split('([a-zA-Z])', d)
    instruction = None
    params = []
    nparams = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if re.match('[a-zA-Z]', part):
            assert not len(params), params
            assert nparams == 0, nparams
            assert part in instruction_options, part
            instruction = part
            # at least one
            nparams = instruction_options[instruction]
            if not instruction_options[instruction]:
                instruction_list.append((instruction, []))
            continue
        assert instruction, part
        for param in re.split('[^0-9.-]+', part):
            if not len(param):
                continue
            param = float(param)
            if nparams == 0:
                nparams = instruction_options[instruction]
            params.append(float(param))
            nparams -= 1
            if nparams == 0:
                assert len(params) == instruction_options[instruction]
                instruction_list.append((instruction, params))
                params = []
                if instruction == 'm':
                    instruction = 'l'
                elif instruction == 'M':
                    instruction = 'L'
    assert nparams == 0

    paths = [[], ]
    paths2 = [[], ]
    sub_point = None
    first_point = None
    last_point = point.copy()
    origin = numpy.matrix([[0.], [0.], [1.]])
    horiz = numpy.matrix([[1., 0., 0.], [0., 0., 0.], [0., 0., 1.]])
    vert = numpy.matrix([[0.,0.,0.],[0.,1.,0.],[0.,0.,1.]])

    for command, params in instruction_list:
        if command in 'mM':
            paths.append([])
            if command == 'M':
                point = origin.copy()
            else:
                command = 'M'
            coords = (point + transform * numpy.matrix([[params[0]], [params[1]], [0]]), )
            point = coords[0].copy()
            sub_point = point.copy()
        elif command in 'zZ':
            point = sub_point.copy()
            sub_point = None
            command = 'L'
            coords = (point.copy(), )
        elif command in 'Cc':
            if command == 'C':
                point = origin.copy()
            else:
                command = 'C'
            coords = (
                point + transform * numpy.matrix([[params[0]], [params[1]], [0]]),
                point + transform * numpy.matrix([[params[2]], [params[3]], [0]]),
                point + transform * numpy.matrix([[params[4]], [params[5]], [0]]),
                )
            point = coords[2].copy()
        elif command in 'lL':
            if command == 'L': 
                point = origin.copy()
            else:
                command = 'L'
            coords = (point + transform * numpy.matrix([[params[0]], [params[1]], [0]]), )
            point = coords[0].copy()
        elif command in 'vV':
            if command == 'V':
                point[1][0] = params[0]
            else:
                point[1][0] += params[0]
            coords = (point.copy(), )
            command = 'L'
        elif command in 'hH':
            if command == 'H':
                point[0][0] = params[0]
            else:
                point[0][0] += params[0]
            coords = (point.copy(), )
            command = 'L'
        else:
            raise Exception, command

        # avoid duplicate points
        if command == 'M' or distance(point, last_point) > minimum_distance:
            paths[-1].append([command, coords])
            last_point = point.copy()
            
    paths = [deque(path) for path in paths if len(path) > 1]
    return paths


def svg_extract_paths(soup, transform=None, point=None):
    origin = numpy.matrix([[0.], [0.], [1.]])
    if transform is None:
        transform = numpy.matrix([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    if point is None:
        point = origin.copy()
    paths = []
    if not hasattr(soup, 'name'):
        return paths
    if soup.has_key('transform'):
        new_transform = decode_transform(soup['transform'])
        transform = new_transform * transform
        point += new_transform * origin.copy()
    if soup.name == u'path':
        if not soup.has_key('d'):
            return paths
        return split_paths(soup['d'], transform.copy(), point.copy())
    if soup.name in ['g', 'svg']:
        for child in soup.contents:
            for path in svg_extract_paths(child, transform.copy(), point.copy()):
                paths.append(path)
                
    return paths

def inxpoint(inx):
    return inx[1][-1]

def plottify_closed(paths):
    for path in paths:
        if distance(inxpoint(path[0]), inxpoint(path[-1])) > 1:
            log.debug('open path')
            continue
        log.debug('closed path')

        move = path.popleft()

        max_linear_dist = None
        max_linear_index = None
        for i in range(len(path)):
            if path[i][0] == 'L':
                dist = distance(inxpoint(path[i]), inxpoint(path[i-1]))
                if max_linear_index == None or dist > max_linear_dist:
                    max_linear_dist = dist
                    max_linear_index = i
        if max_linear_index is not None and max_linear_dist > 10:
            path.rotate(-max_linear_index)
            point_f = inxpoint(path[-1])
            point_t = inxpoint(path[0])
            v = (point_t - point_f)
            v_unit = v / magnitude(v)
            centre_1 = point_f + v * .5 - v_unit * 5
            centre_2 = point_f + v * .5 + v_unit * 5
            path.append( ['L', [centre_2, ] ] )
            path.appendleft(['M', [centre_1, ] ] )
        else:
            path.appendleft(['M', [inxpoint(path[-1]),]])
            path.append( path[1] )
            



def svg_text_to_plotcutsvg(svg_text):
    BeautifulStoneSoup.NESTABLE_TAGS["g"] = []
    svg_soup = BeautifulStoneSoup(svg_text, selfClosingTags=['path'])
    svg_soup = svg_soup.findChild('svg')
    assert svg_soup

    paths = svg_extract_paths(svg_soup)
    assert paths

    plottify_closed(paths)
        
    plotcut_svg = absolute_paths_to_plotcut_svg(paths)

    return plotcut_svg



def svg_file_to_plotcutsvg(filename):
    svg_text = codecs.open(filename, 'r', 'utf-8').read()
    return svg_text_to_plotcutsvg(svg_text)



if __name__ == '__main__':
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.WARNING)

    usage = """%prog FILE"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbosity",
                      help="Print verbose information for debugging.", default=1)
    parser.add_option("-q", "--quiet", action="store_const", const=0, dest="verbosity",
                      help="Suppress warnings.", default=1)
    
    (options, args) = parser.parse_args()
    
    if options.verbosity > 2:
        log.setLevel(logging.DEBUG)
    elif options.verbosity == 2:
        log.setLevel(logging.INFO)
    elif not options.verbosity:
        log.setLevel(logging.ERROR)

    if not len(args):
        parser.print_usage()
        sys.exit(1)

    print svg_file_to_plotcutsvg(arg)

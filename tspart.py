# coding=utf-8
# tspart.py
# 3/7/2012
#
# Interpret the black bits in a black & white bit map as "cities" on a
# rectangular map.  Use the coordinates of these cities (bits) as input
# to a TSP solver by converting the coordinates of the cities to a TSPLIB
# file.
#
# Then, generate a fast, approximate solution to the resulting TSP using
# the linkern solver from Concorde TSP.  Using the solution from the
# solver -- a "tour" -- generate an SVG plot of the tour.
#
#    python tspart.py [input-bitmap-file [output-svg-file]]
#
# If no input file name is supplied, they you will be prompted for the
# name of an input and output file.  If no output file name is supplied,
# then it will have a name similar to the input file but with a ".svg"
# extension.
#
# Presently, the input file formats supported are
#
# .PBM -- Portable Bit Map files (Raw or ASCII; P4 or P1)
#
# .PTS -- File of (x, y) or (x, y, radius) coordinates.  Must have as the
#         first line the literal string
#
#            # x-coord y-coord radius
#
#         Subsequent lines must then be either
#
#            x-coordinate y-coordinate radius
#
#         or
#
#            x-coordinate y-coordinate
#
#         where "x-coordinate", "y-coordinate", and "radius" are the ASCII
#         representation of floating point numbers.  E.g.,
#
#            # x-coord y-coord radius
#            0.0210369 0.00199109 0.0022353
#            0.0255807 0.00200347 0.00216036
#            0.115518 0.00203477 0.00263275
#
#         The radii are ignored.


# Written by Daniel C. Newman for the Eggbot Project
# dan dot newman at mtbaldy dot us
# 25 September 2010

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import tempfile
import shutil

from tspbitcity import TSPBitCity
from tspsolution import TSPSolution

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", type=str, help="Path to input file")
    parser.add_argument('-o', "--output", type=str, help="Path to output file")

    parser.add_argument("-c", '--count', help='Report the number of stipples in the input file and then exit', action="store_true")
    parser.add_argument("-f", '--fill', type=str, default='none',
                        help='Fill color (e.g., red, blue, #ff0000); requires --max-segments=0')
    parser.add_argument("-L", '--layer', type=str, default=None, help='Layer name')
    parser.add_argument('-m', '--max-segments', type=int, default=40000000000000,
                        help='Maximum number of line segments per SVG <path> element')
    parser.add_argument('--mid', help='Produce output with only the SVG preamble (--pre), postamble (--post), or neither (--mid)', action="store_true")
    parser.add_argument('--pre', help='Produce output with only the SVG preamble (--pre), postamble (--post), or neither (--mid)', action="store_true")
    parser.add_argument('--post', help='Produce output with only the SVG preamble (--pre), postamble (--post), or neither (--mid)', action="store_true")
    parser.add_argument('-r', '--runs', type=int, default=1, help='Number of linkern runs to take')
    parser.add_argument('-s', '--stroke', type=str, default='#000000', help='Stroke (line) color (e.g., black, green, #000000')
    parser.add_argument('-S', '--solver', type=str, default='linkern', help='Path to the linkern executable (example: "linkern" in *nix, "C:/linkern.exe" in Windows')
    args = parser.parse_args()

    if args.pre:
        file_contents = 1
    elif args.mid:
        file_contents = 0
    elif args.post:
        file_contents = 2
    else:
        # Complete SVG file
        file_contents = 3

    # Enforce -max-segments=0 when --fill is used
    if args.max_segments and args.fill != 'none':
        sys.stderr.write('Use of -f or --fill requires -max-segments=0\n')
        sys.exit(1)

    # Convert files to absolute files
    args.input = os.path.abspath(args.input.strip())
    if not os.path.exists(args.input):
        sys.stderr.write('File "{}" does not exist!\n'.format(args.input))
        sys.exit(1)

    # Now do some fixups, including defaulting the output file name
    raw_path_without_ext, input_ext = os.path.splitext(args.input)
    filename_without_ext = os.path.split(raw_path_without_ext)[1]
    if input_ext in ['.pbm', '.pts']:
        solution_filepath = filename_without_ext + ".tour"
        if args.output is None:
            args.output = raw_path_without_ext + '.svg'
    elif input_ext in ['.PBM', '.PTS']:
        solution_filepath = filename_without_ext + ".TOUR"
        if args.output is None:
            args.output = raw_path_without_ext + '.SVG'
    else:
        solution_filepath = filename_without_ext + ".tour"
        if args.output is None:
            args.output = raw_path_without_ext + '.svg'

    # Place the solution file into the temporary directory.  We don't need to
    # worry (too much) about creating it: we're going to make some other calls
    # to open a temporary file and those calls should instantiate the directory.
    # And, since we check for errors on those calls, we should catch any problems.
    solution_filepath = os.path.join(tempfile.gettempdir(), os.path.basename(solution_filepath))

    # Load the bitmap file
    print('Loading bitmap file {} ... '.format(args.input))
    cities = TSPBitCity()
    if not cities.load(args.input):
        sys.exit(1)
    print('done; {} stipples'.format(len(cities.coordinates)))
    if args.count:
        sys.exit(0)

    # Open a temporary file to hold the TSPLIB file
    tmp_dir = tempfile.mkdtemp()
    tmp_filename = filename_without_ext + '.tsp'
    tspfile_path = os.path.join(tmp_dir, tmp_filename)

    # Now write the TSPLIB file
    print('Writing TSP solver input file {} ... '.format(tspfile_path))
    cities.write_tspfile(tspfile_path)
    print('done')

    # Run the solver
    print('Running TSP solver ... ')
    cmd = [args.solver, '-r', str(args.runs), '-o', solution_filepath, tspfile_path]
    status = subprocess.call(cmd, shell=False)

    # Remove the temporary directory
    shutil.rmtree(tmp_dir)

    # Did the solver succeed?
    if status:
        # No, something went wrong
        sys.stderr.write('Solver failed; status = {}\n'.format(status))
        os.unlink(solution_filepath)
        sys.exit(1)

    # Solver succeeded
    print('\nSolver finished successfully')

    # Load the solution (a tour)
    print('Loading solver results from {} ... '.format(solution_filepath))
    solution = TSPSolution()
    if not solution.load(solution_filepath):
        sys.stderr.write('Unable to load the solution file\n')
        os.unlink(solution_filepath)
        sys.exit(1)
    print('done')

    # Remove the tour file
    os.unlink(solution_filepath)

    # Now write the SVG file
    print('Writing SVG file {} ... '.format(args.output))
    if not cities.write_tspsvg(args.output, solution.tour, args.max_segments,
                               args.stroke, args.fill, file_contents,
                               args.layer):
        # write_tspsvg() takes care of removing outfile in the case of an error
        sys.stderr.write('Error writing SVG file\n')
        sys.exit(1)
    print('done')

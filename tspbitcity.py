# coding=utf-8
# tspbitcity.py
# 9/26/2010-A

# Python class which interprets the black bits in a black & white bitmap
# as the coordinates of "cities" on a map.  Turn these coordinates into a
# TSPLIB file for use as input to a TSP solver.

# Point output files from Adrian Secord's Weighted Voronoi Stippler are
# also recognized.  The coordinates from those files are floating point
# numbers and are rescaled to the range [0, 800] and converted to integers.
# The reason for this isn't for the TSP solver -- it handles floats just
# fine.  Rather, to have (1) have a consistent data type, and (2) the
# resulting SVG file is much smaller when integers are used as the
# coordinates.

# This file can also be run as a standalone program to produce a TSPLIB
# file from a bitmap:
#
#    python tspbitcity.py [input-bitmap-file [output-tsplib-file]]

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

from __future__ import division

import argparse
import os
import sys
from cgi import escape

try:
    input = raw_input  # Python 2
except NameError:
    pass  # Python 3


class TSPBitCity(object):
    # When presented with a collection of floating point (x,y) coordinates,
    # we normalize their bounding box to have a height and width of BOXSIZE
    BOXSIZE = float(800)

    def __init__(self):

        # We save the input bitmap file name for purposes of error reporting
        # and generating a default output file name

        self.infile = ''

        # Our width and height correspond to the size of the input bitmap
        # All coordinates (x, y) will satisfy 0 <= x < width and
        # 0 <= y < height

        self.width = 0
        self.height = 0

        # Our list of "city" (x, y) coordinates
        # Each member of the list is a 2-tuple (x, y) which satisfies
        # 0 <= x < width and 0 <= y < height
        #
        # Owing to the nature of our input bitmaps and the way we read them,
        # coordinate[i] = (x[i], y[i]) and coordinate[i+1] = (x[i+1], y[i+1])
        # will always satisfy
        #
        #     y[i] >= y[i+1]
        #
        # and if y[i] == y[i+1], then x[i] < x[i+1].  In other words, the
        # cities are sorted such that their y coordinates decrease as you
        # advance through the list of coordinates.

        self.coordinates = []

    # Load a PBM of type P4
    def __load_pbm_p4(self, f):
        if self.width <= 0:
            raise ValueError("Width of {} must be greater than 0".format(self.infile))
        if self.height <= 0:
            raise ValueError("Height of {} must be greater than 0".format(self.infile))

        self.coordinates = []

        # PBM file goes from the top of the bitmap (y = h-1) to the
        # bottom of the bitmap (y = 0), and from the left of the bitmap
        # (x = 0) to the right of the bitmap (x = w)

        # Each line of the file contains w pixels with 8 pixels per byte
        # So, each line of the file must be (w + 7) >> 3 bytes long
        nbytes = (self.width + 7) >> 3

        # Each line of the file from here on out corresponds to a
        # single row of the bitmap

        for row in range(self.height - 1, -1, -1):

            # Read the bitmap row
            row_bytes = f.read(nbytes)

            # Perform a sanity check
            if (row_bytes == b'') or (row_bytes == b'\n'):
                sys.stderr.write('1 Premature end-of-data encountered in {}\n'.format(self.infile))
                return False

            # And start at the first byte of the line read
            column_byte_index = 0

            # initialize the steps
            column_byte = row_bytes[column_byte_index]
            pixel_mask = 0b10000000

            # Now process this row from left to right, x = 0 to x = w - 1
            for column in range(0, self.width):

                # Hack for Python2/3 compatibility
                # Convert the unsigned char byte to an integer
                if not isinstance(column_byte, int):
                    column_byte = ord(column_byte)

                # See if this bit is lit
                if pixel_mask & column_byte:
                    # Bit is lit, save the coordinate of this pixel
                    self.coordinates.append((column, row))

                # Now move our bitmask bit to the right by one pixel
                pixel_mask >>= 1

                # See if it's time to move to the next byte in the input line
                # Reinitialize the steps
                if pixel_mask == 0x00:
                    column_byte_index += 1
                    if column_byte_index < nbytes:
                        column_byte = row_bytes[column_byte_index]
                        pixel_mask = 0b10000000
                    elif column < (self.width - 1):
                        # Something has gone wrong: we didn't read enough bytes?
                        sys.stderr.write('2 Premature end-of-file encountered in {}\n'.format(self.infile))
                        return False

        return True

    # Load a PBM of type P1
    def __load_pbm_p1(self, f):

        if self.width <= 0:
            raise ValueError("Width of {} must be greater than 0".format(self.infile))
        if self.height <= 0:
            raise ValueError("Height of {} must be greater than 0".format(self.infile))

        self.coordinates = []

        # PBM file goes from the top of the bitmap (y = h-1) to the
        # bottom of the bitmap (y = 0), and from the left of the bitmap
        # (x = 0) to the right of the bitmap (x = w)

        # Each line of the file contains a string of one or more characters
        # from the alphabet { '0', '1', '#', '\n' } where
        #
        #   '0' -- a zero bit in the bitmap
        #   '1' -- a one bit in the bitmap
        #   '#' -- introduces a comment line
        #   '\n' -- a line record terminator
        #
        # Note the last line of the file may possibly omit the trailing LF.
        # That is normal for PBM files of type P1.
        #
        # Each line from the file may be a portion of one or more rows
        # of the bitmap.  So, it's up to use to track which row and column
        # we are at in the bitmap.

        # Our column index
        column = 0

        # Our row index.  Recall that we start at the top row, row h - 1
        row = self.height - 1

        # Now loop over the remaining lines in the file
        # Note that the file line of a P1 PBM file usually does not
        # end with a LF record terminator

        for line in f:

            # Ignore semantically empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Too much data in the file?
            if row < 0:
                sys.stderr.write('Too much data in {}\n'.format(self.infile))
                return False

            # Loop over each byte in the line
            for each_byte in line:

                if each_byte == '1':
                    self.coordinates.append((column, row))
                elif each_byte != '0':
                    sys.stderr.write('Invalid content in %s\n' % self.infile)
                    return False

                # Move to the next column
                column += 1

                # Have we finished this row?
                if column >= self.width:
                    # Finished a row, move down to the next row
                    column = 0
                    row -= 1

        # All done
        # Perform a sanity check: we should be at the start of row -1
        if (column == 0) and (row == -1):
            return True

        # Something bad happened
        sys.stderr.write(' Premature end-of-file encountered in %s\n' % self.infile)
        return False

    # Load a file in which each line has the format
    #
    #    x-coord y-coord radius

    def __load_xyr(self, f):

        self.coordinates = []
        self.width, self.height = int(self.BOXSIZE), int(self.BOXSIZE)
        px, py = [], []

        for line in f:

            # Ignore comment lines
            if line.startswith('#'):
                continue

            vals = line.strip().split(' ')
            if len(vals) not in [2, 3]:
                sys.stderr.write('Invalid content in file %s\n' % self.infile)
                return False

            px.append(float(vals[0]))
            py.append(float(vals[1]))

        # Find the extrema
        fmin = min(min(px), min(py))
        fmax = max(max(px), max(py))

        # We will translate bounding box containing the points to have
        # it's bottom, left corner at (0, 0).  Further we will scale the
        # box to have height and width of BOXSIZE (e.g., 800).  Then
        # we convert the floating point values to integers

        # Note we pretend the points all have radius zero....

        span = float(fmax - fmin)
        scale = self.BOXSIZE / span if span > 0 else 1
        # Can't do "for x, y in px, py:" as the lists are too large
        # resulting in 'too manu values to unpack'
        for i in range(0, len(px)):
            self.coordinates.append((int(round((px[i] - fmin) * scale)),
                                     int(round((py[i] - fmin) * scale))))

        return True

    def load(self, infile):

        self.infile = infile

        # Open the input file
        # This may raise an exception which is fine by us
        with open(self.infile, 'rb') as f:

            # Get the magic number
            # For PBM files this will always be two bytes followed by a \n
            # For other image types, this line could be who knows what.  Hence
            # our use of a size argument to readline()
            magic_number = f.readline(4)

            # PBM files must be P1 or P4
            if magic_number in [b'P4\n', b'P1\n']:

                # File is a PBM bitmap file

                # Loop until we read the bitmap dimensions
                # NOTE: we cannot use "while line in f:" since that is incompatible
                # with later using f.read().  If the file is of type P4, then we
                # will need to use f.read() to obtain the bitmap

                self.width, self.height = (0, 0)
                while True:
                    line = f.readline()
                    if not line.startswith(b'#'):
                        self.width, self.height = tuple(map(int, line.split()))
                        break

                # Did we actually read anything (useful)?
                if not self.width or not self.height:
                    sys.stderr.write('Unable to read sensible bitmap dimensions for {}\n'.format(self.infile))
                    return False

                # Now read the bitmap
                # cities will be a list of 2-tuples, each 2-tuple being the (x, y)
                # coordinate of a 1 bit in the bitmap.  These (x, y) coordinates
                # correspond to row and column numbers with
                #
                #    0 <= row <= height - 1
                #    0 <= column <= width - 1
                #
                # row = 0 corresponds to the bottom of the bitmap
                # column = 0 corresponds to the left edge of the bitmap

                ok = self.__load_pbm_p4(f) if magic_number == b'P4\n' else self.__load_pbm_p1(f)

            elif magic_number == b'# x-':

                # File may be an (x, y, radius) coordinate file
                line = f.readline().strip()
                if line != 'coord y-coord radius':
                    sys.stderr.write('Input file {} is not a supported file type\n'.format(self.infile))
                    sys.stderr.write('Must be a PBM file or file of (x, y) coordinates. [err=1]\n')
                    return False

                ok = self.__load_xyr(f)

            else:

                # Unsupported file type
                sys.stderr.write('Input file {} is not a supported file type\n'.format(self.infile))
                sys.stderr.write('Must be a PBM file or file of (x, y) coordinates. [err=2]\n')
                return False

        # If ok is False, then __load_xxx() will have printed an error
        # message already
        return ok

    def write_tspfile(self, outfile='', f=None, infile='TSPART'):

        if not f:
            # Deal with funky outfile names
            if not outfile:
                if self.infile.endswith('.pbm'):
                    outfile = self.infile[:-3] + 'tsp'
                elif self.infile.endswith('.PBM'):
                    outfile = self.infile[:-3] + 'TSP'
                else:
                    outfile = self.infile + '.tsp'

            # Create the output file
            # This may generate an exception which is fine by us
            f = open(outfile, 'w')

        # And now write the contents of the TSPLIB file
        try:
            # Header
            f.write('NAME:{}\n'.format(infile))
            f.write('TYPE:TSP\n')
            f.write('DIMENSION:{:d}\n'.format(len(self.coordinates)))
            f.write('EDGE_WEIGHT_TYPE:EUC_2D\n')
            f.write('NODE_COORD_TYPE:TWOD_COORDS\n')

            # list of coordinates
            f.write('NODE_COORD_SECTION:\n')
            city_number = 0
            for city in self.coordinates:
                f.write('{:d} {:d} {:d}\n'.format(city_number, city[0], city[1]))
                city_number += 1

            # And finally an EOF record
            f.write('EOF:\n')

        except:
            # Remove the incomplete file
            # Note on Windows we must close the file before deleting it
            f.close()
            if outfile != '':
                os.unlink(outfile)
            # Now re-raise the exception
            raise

        f.close()

    # max_segments == 0 implies unlimited number of segments per path
    def write_tspsvg(self, outfile, tour, max_segments=400,
                     line_color='#000000', fill_color='none',
                     file_contents='3', label=None):

        if max_segments < 0:
            raise ValueError("Max Segments must be greater than 0.")

        # max_segments will limit number of points in the path and hence we need
        # Note that previously we ensured that max_segments >= 0
        if max_segments:
            max_segments += 1

        # Default line color to black
        if not line_color:
            line_color = '#000000'

        # Note, we only ask for a fill color when we know we're drawing
        # a single, closed path
        if fill_color:
            fill_color = fill_color.strip('"\'')
        if not fill_color or max_segments:
            fill_color = 'none'

        f = open(outfile, 'w')

        # Write the SVG preamble?
        if 1 & int(file_contents):
            f.write(
                '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
                '<!-- Created with the Eggbot TSP art toolkit (http://egg-bot.com) -->\n'
                '\n'
                '<svg xmlns="http://www.w3.org/2000/svg"\n'
                '     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
                '     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"\n'
                '     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
                '     xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
                '     xmlns:cc="http://creativecommons.org/ns#"\n'
                '     height="{h}"\n'
                '     width="{w}">\n'
                '  <sodipodi:namedview\n'
                '            showgrid="false"\n'
                '            showborder="true"\n'
                '            inkscape:showpageshadow="false"/>\n'
                '  <metadata>\n'
                '    <rdf:RDF>\n'
                '      <cc:Work rdf:about="">\n'
                '        <dc:format>image/svg+xml</dc:format>\n'
                '        <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n'
                '        <dc:subject>\n'
                '          <rdf:Bag>\n'
                '            <rdf:li>Egg-Bot</rdf:li>\n'
                '            <rdf:li>Eggbot</rdf:li>\n'
                '            <rdf:li>TSP</rdf:li>\n'
                '            <rdf:li>TSP art</rdf:li>\n'
                '          </rdf:Bag>\n'
                '        </dc:subject>\n'
                '        <dc:description>TSP art created with the Eggbot TSP art toolkit (http://egg-bot.com)</dc:description>\n'
                '      </cc:Work>\n'
                '    </rdf:RDF>\n'
                '  </metadata>\n'.format(h=self.height, w=self.width))

        if label:
            f.write('inkscape:groupmode="layer" inkscape:label="{}"\n'.format(escape(label, quote=True)))

        f.write('>\n')

        max_index = len(self.coordinates)
        last_city = None
        path = False
        first_path = True
        points = 0

        for city_idx in tour:

            city_index = int(city_idx)
            if (city_index < 0) or (city_index >= max_index):
                sys.stderr.write('TSP tour contains an invalid city index, {}\n'.format(city_index))
                f.close()
                os.unlink(outfile)
                return False

            if not path:
                # We need to start a new path whose first point is the
                # last city we moved to
                path = True
                if not last_city:
                    last_city = self.coordinates[city_index]

                last_city_y = self.height - last_city[1]
                f.write('    <path style="fill:{};stroke:{};stroke-width:1"\n'.format(fill_color, line_color) +
                        '          d="m {:d},{:d}'.format(last_city[0], last_city_y))
                if points == 0:
                    # This is the first path so skip the next step
                    continue

            # Now move to the current city
            next_city = self.coordinates[city_index]
            next_city_x = next_city[0] - last_city[0]
            next_city_y = (next_city[1] - last_city[1]) * -1

            f.write(' {:d},{:d}'.format(next_city_x, next_city_y))
            last_city = next_city
            points += 1

            if max_segments and points > max_segments:
                # Start a new path
                path = False
                first_path = False
                points = 1  # 1 and not 0
                f.write('"/>\n')

        # Close out any open path
        if path:
            if first_path:
                # Make sure it's known that this is a single, closed path
                # Note: if we wrote a single path but closed it out because
                # len(tour) == max_segments + 1, then this final 'Z' will be omitted
                # which should be okay anyway.
                f.write(' Z"/>\n')
            else:
                f.write('"/>\n')

        # Write the SVG postamble?
        if 2 & int(file_contents):
            f.write('</svg>\n')

        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", type=str, help="Path to input file")
    parser.add_argument('-o', "--output", type=str, help="Path to output file")
    args = parser.parse_args()

    # Convert files to absolute files
    args.input = os.path.abspath(args.input.strip())
    if not os.path.exists(args.input):
        sys.stderr.write('File "{}" does not exist!\n'.format(args.input))
        sys.exit(1)

    # Now do some fixups, including defaulting the output file name
    raw_path_without_ext, input_ext = os.path.splitext(args.input)
    tmp_filename_without_ext = os.path.split(raw_path_without_ext)[1]
    if args.output is None:

        if input_ext in ['.pbm', '.pts']:
            args.output = raw_path_without_ext + '.tsp'
        elif input_ext in ['.PBM', '.PTS']:
            args.output = raw_path_without_ext + '.TSP'
        else:
            args.output = raw_path_without_ext + '.tsp'

    citymap = TSPBitCity()
    if not citymap.load(args.input):
        sys.exit(1)

    citymap.write_tspfile(args.output)

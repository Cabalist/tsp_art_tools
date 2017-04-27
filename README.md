# Art Tools for GoCupi

##Summary
This repository contains code that assists in converting images to be used by the *gocupi* Polar plotter (www.gocupi.com)

*Gocupi* can draw ANY IMAGE!  As long as the image is an SVG with only straight lines. :) This presents some challenges if you want to draw a photo or complicated art.  These scripts are part of the process to get an image converted over to something *gocupi* can understand.

The basic steps are:  

- Convert your image to a bunch of dots using Gimp. A process called Stippling. It looks like this:  
 <Insert image>  

- Connect those dots with straight lines to create shading and weight to your drawing.  (That is what these scripts do!) Looks like this:  
 <Insert Image>

- Cleanup stray lines using Gimp again. Final looks like this:  
 <Insert Image>
 
- Draw with gocupi! Looks like this:  
  <insert Image>


## Quickstart
1. Install the necessary dependecies
2. Stipple your image using Gimp
3. Run `python3 tspart.py ./path/to/your/image.jpg`  
    This will generate `image.svg` in your image path
4. **OPTIONAL** Remove unnecssary lines in Gimp 
5. Use `gocupi svg 200 image.svg` to create your image

## Installation
This package has no python dependencies but it does require an external package to create the paths.  This package does the hard math of figuring out the best path in between the dots.

#### OS X:

  Install homebrew (https://brew.sh/)
  run brew install homebrew/science/concorde`

#### Windows:
  While binary executables are available for concorde and linkern for
  Windows, they require a minimal cygwin install.  See
  http://www.tsp.gatech.edu/concorde/downloads/downloads.htm


## Overview of scripts

#### tspart.py
  Python script to accept as input a black and white bitmap file in PBM
  format and produce as output a SVG file (TSP art) arrived at by using
  the fast, heuristic TSP solver linkern.

  In addition to PBM files, a simple format allowing (x, y) or (x, y, radius)
  coordinates is also supported.  (E.g., the format output by some stippling
  software.) See the comments in tspbitcity.py for further details.

#### tspbitcity.py
  Python class used by tspart.py.  This is the class which reads in a
  PBM file and can generate a TSPLIB format file for concorde and linkern.
  Also, using a TSP tour, it can generate an SVG file.

  If run as a standalone Python script, tspbitcity.py will generate a
  TSPLIB file from a PBM file.

#### tspsolution.py
  Python class used by tspart.py.  This class reads a solution file from
  either concorde or linkern and determines the "tour".  This "tour" is
  then used by tspart.py to generate the output SVG file.


## Stippling Instructions

1. Load your image into Gimp
2. Convert to grayscale: Image > Mode > Grayscale
3. Wash out the image
   a. Colors > Levels...
   b. Set the "All Channels" under "Output Levels" to 180 - 245
4. Dither the image
   a. Image > Mode > Indexed...
   b. Select "Use black and white (1-bit palette) under "Colormap"
   c. Select "Floyd-Steinberg (normal) under "Color dithering"
   d. Click "Convert" button
5. Save the file as a PBM format file; choose "raw" when asked

If step 4 produces too many points, then start over (edit undo) until
your back to the grayscale image.  Then try scaling the image down to 50%,
25%, or more with Image > Scale Image....

Also see this great video here: https://youtu.be/TKy2fxsmssg?t=7m29s
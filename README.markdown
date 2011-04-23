# plotcut

Optimises SVG vector files for sending to a cutting plotter.

## Requirements

-   [Python](http://www.python.org/)
-   [NumPy](http://numpy.scipy.org/)
-   [Mako](http://www.makotemplates.org/)
-   [BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/)

## Usage

    plotcut.py in.svg > out.svg

## Process

-   Converts all path objects to open paths of 0.03mm width
-   Discards all other objects
-   Promotes all paths to top-level objects by removing them from any hierarchy while preserving transformations.
-   Creates an overlap on any closed paths to avoid gaps between the start and end points caused by the length of the plotter knife
    -   For paths that contain any long, straight edges, this is a small overlap at the middle of the longest straight edge
    -   For all other paths the whole first edge segment is repeated at the end of the path.

## Limitations

-   Does not support the following SVG path commands (which will cause a fatal error): SsQqTtAa.

## References

1.   [W3C SVG Paths specification][1]

[1]:(http://www.w3.org/TR/SVG/paths.html)
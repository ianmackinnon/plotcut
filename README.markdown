# plotcut

Optimises SVG vector files for sending to a cutting plotter.

## Usage

    plotcut.py in.svg > out.svg

## Process

-   Convert all path objects to open paths of 0.03mm width
-   Discards all other objects
-   Promotes all paths to top-level objects by removing them from any hierarchy while preserving transformations.
-   Creates an overlap on any closed paths to avoid gaps between the start and end points caused by the length of the plotter knife
    -   For paths that contain any long, straight edges, this is a small overlap at the middle of the longest straight edge
    -   For all other paths the whole first edge segment is repeated at the end of the path.
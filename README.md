This repository includes data from multiple sources, and a script which consolidates the data to create a flat list of annotated GeoJSON objects representing the boundaries of a large number of places in Canada:

* The nation of Canada itself (taken from ne_10m_admin_0_countries.zip)
* Each province (taken from gpr_000b11a_e.zip)
* Each census division that corresponds to a county, but not other census divisions (taken from gcd_000b11a_e.zip)
* Each population center - towns and cities (taken from gpc_000b11a_e.zip)

I examined these census data files and decided not to
incorporate them into the dataset, at least for now:

* Census metropolitan area and agglomerations - `gcma000b11a_e.zip` -
  This only covers the largest cties, so it's redundant.
* Census subdivisions - `gcsd000b11a_e.zip` -
  Most census subdivisions are administrative boundaries that don't
  seem to correspond to the places people think of as their 'home town'.
* Designated places - `gdpl000b11a_e.zip` - These are very small communities
  and I don't yet understand how they interact with the census subdivisions.

Generating the list is as simple as 1-2-3:

```
sh 1-extract.sh
sh 2-convert.sh
python 3-consolidate.py > places.ndjson
```

Running the script requires that `ogr2ogr` be installed (it's
available in the Debian package `gdal-bin`) and that the `geojson`
Python library be installed.



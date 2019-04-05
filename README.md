This repository includes data from multiple sources, and a script which consolidates the data to create a flat list of annotated GeoJSON objects representing the boundaries of a large number of places in Canada:

* The nation of Canada itself
* Each province (taken from gpr_000b11a_e.zip)
* Each census division (e.g. cities and towns) (taken from gcd_000b11a_e.zip)
* Each designated place (taken from gdpl000b11a_e.zip)

Generating the list is as simple as 1-2-3:

```
sh 1-extract.sh
sh 2-convert.sh
python 3-consolidate.py > places.ndjson
```

Running the script requires that `ogr2ogr` be installed (it's
available in the Debian package `gdal-bin`) and that the `geojson`
Python library be installed.

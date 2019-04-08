This repository includes data from multiple sources, and a script which consolidates the data to create a flat list of annotated GeoJSON objects representing the boundaries of a large number of places in Canada:

* The nation of Canada itself (taken from ne_10m_admin_0_boundary_lines_land.zip)
* Each province (taken from gpr_000b11a_e.zip)
* Each census division (~counties) (taken from gcd_000b11a_e.zip)

---
Which of these is the best bet for cities???

* Census subdivisions - gcsd000b11a_e.zip
* Census metropolitan area and agglomerations - gcma000b11a_e.zip
* Census population centers - gpc_000b11a_e.zip
---

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

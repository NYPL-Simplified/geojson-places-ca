import logging
import os
import geojson
import json
import re
import unicodedata
from pdb import set_trace

cb_input_dir = "2-ca-geojson"

def ascii_alias(s):
    """If this name contains combining characters, return the
    version without combining characters for use as an alias.
    """
    if not s:
        return None
    if isinstance(s, str):
        s = s.decode("utf8")
    try:
        ascii = s.encode("ascii")
        return None
    except Exception, e:
        pass
    alias = ''.join(c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn')
    if alias == s:
        return None
    return alias
    
def features(filename, encoding='windows-1252'):
    path = os.path.join(cb_input_dir, filename)
    data = open(path).read().decode(encoding)
    collection = geojson.loads(data)
    for feature in collection.features:
        yield feature

class Place(object):

    def __init__(self, type, geography, id, name,
                 french_name=None,
                 abbreviated_name=None, parent=None,
                 parent_id=None,
    ):
        """Rationalizes geographic data from multiple scales into a single
        format.
        """
        self.type = type
        self.geography = geography
        self.id = id
        self.name = name
        self.abbreviated_name = abbreviated_name
        self.french_name = french_name
        self.parent = parent
        self.parent_id = parent_id
        self.aliases = set()

        # If the name or its abbreviation contains diacritics, create
        # an ASCII version to serve as an alias.
        aliases = map(ascii_alias,
                      [self.name, self.abbreviated_name, self.french_name])
        for x in aliases:
            if x:
                self.aliases.add(x)

    @property
    def output(self):
        """A Place is output as two lines: one containing metadata
        and one containing a GeoJSON object.
        """
        return "\n".join([json.dumps(self.jsonable), json.dumps(self.geography)])
        
    @property
    def jsonable(self):
        data = dict(type=self.type, id=self.id, name=self.name)
        if self.abbreviated_name:
            data['abbreviated_name'] = self.abbreviated_name
        if self.aliases or self.french_name:
            aliases = []
            data['aliases'] = aliases
            for alias in self.aliases:
                if alias != self.name and alias != self.french_name:
                    aliases.append(dict(name=alias, language='eng'))
        if self.french_name:
            aliases.append(dict(name=self.french_name, language='fre'))
        if self.parent:
            data['parent_id'] = self.parent.id
        elif self.parent_id:
            data['parent_id'] = self.parent_id
        else:
            data['parent_id'] = None
        return data

    def __repr__(self):
        data = self.jsonable
        return json.dumps(data)


class Nation(Place):

    @classmethod
    def from_filename(self, filename, look_for):
        for nation in features(filename, 'utf8'):
            properties = nation.properties
            if properties['NAME_EN'] != look_for:
                continue
            abbreviation = properties['ISO_A2']
            return Nation(
                'nation', nation['geometry'], abbreviation,
                properties['NAME_EN'], properties['NAME_FR'],
                abbreviation
            )

    def __init__(self, *args, **kwargs):
        super(Nation, self).__init__(*args, **kwargs)
        self.provinces = []


class Province(Place):

    def __init__(self, *args, **kwargs):
        super(Province, self).__init__(*args, **kwargs)
        self.seen_names = set()

    def saw_place_name(self, name):
        """Record that we saw a record of a place name in this province. This
        will let us ensure that we will not alias a postal code to a
        place name if the place name is already associated with a
        census division.
        """
        self.seen_names.add(name)


class Provinces(object):
    import re
    non_alpha = re.compile("[^A-Z]")

    # The data we have doesn't include the official postal
    # abbreviations for the provinces, so we need to include it here.
    abbreviations = {
        "Alberta": "AB",
        "British Columbia": "BC",
        "Manitoba": "MB",
        "New Brunswick": "NB",
        "Newfoundland and Labrador": "NL",
        "Nova Scotia": "NS",
        "Northwest Territories": "NT",
        "Nunavut": "NU",
        "Ontario": "ON",
        "Prince Edward Island": "PE",
        "Quebec": "QC",
        "Saskatchewan": "SK",
        "Yukon": "YT",
    }

    @classmethod
    def from_filename(cls, filename, nation):
        provinces = cls()
        for province in features(filename):
            props = province.properties
            name = props['PRENAME']
            place = Province(
                'state', province.geometry, id=props['PRUID'],
                name=name, abbreviated_name=cls.abbreviations[name],
                parent=nation, french_name=props['PRFNAME']
            )
            provinces.add(place)
            nation.provinces.append(province)
        return provinces

    def __init__(self):
        self.by_abbreviation = dict()
        self.by_id = dict()

    def add(self, province):
        self.by_abbreviation[province.abbreviated_name] = province
        self.by_id[province.id] = province

class CensusDivisions(object):
    "Census divisions--basically counties."

    @classmethod
    def from_filename(cls, filename, provinces, types=None):
        for division in features(filename):
            properties = division.properties
            province_id = properties['PRUID']
            name = properties['CDNAME']
            id = properties['CDUID']
            if types and properties['CDTYPE'] not in types:
                continue
            yield Place(
                'county', division.geometry, id, name,
                parent=provinces.by_id[province_id]
            )

class Cities(object):
    """Cities and towns."""
    @classmethod
    def from_filename(cls, filename, provinces):
        for city in features(filename):
            properties = city.properties
            province_id = properties['PRUID']
            name = properties['PCNAME']
            id = properties['PCUID']

            # These fields can be used to get more information about the
            # type and size of the population center:
            # 
            # https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/tab/t1_12-eng.cfm
            # type = properties['PCTYPE']

            # https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/tab-eng.cfm
            # cls = properties['PCCLASS']
            yield Place(
                'city', city.geometry, id, name,
                parent=provinces.by_id[province_id],
            )


# Extract a shapefile from Canada from a list of countries.
canada = Nation.from_filename("ne_10m_admin_0_countries.json", "Canada")
print canada.output

# Extract shapefiles for each province and attach them to Canada.
provinces = Provinces.from_filename("gpr_000b11a_e.json", canada)
for province in provinces.by_id.values():
    print province.output

# Attach each county to its province.
# As per https://www150.statcan.gc.ca/n1/pub/92-151-g/2011001/tech-eng.htm,
# * CT and CTY are counties
# * MRC are "county-like political entities" in Quebec
for county in CensusDivisions.from_filename(
    "gcd_000b11a_e.json", provinces, types=('CT', 'CTY', 'MRC')
):
    print county.output

# Attach each city to its province.
for city in Cities.from_filename("gpc_000b11a_e.json", provinces):
    print city.output
 

import logging
import os
import geojson
import json
import re
import unicodedata
from pdb import set_trace

cb_input_dir = "2-ca-geojson"
output_dir = "3-consolidated"

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

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

class Place(object):

    def __init__(self, type, geography, id, name,
                 french_name=None,
                 abbreviated_name=None, parent=None,
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
                aliases.append(dict(name=alias, language='eng'))
        if self.french_name:
            aliases.append(dict(name=self.french_name, language='fre'))
        if self.parent:
            data['parent_id'] = self.parent.id
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

    @classmethod
    def from_filename(cls, filename, nation):
        provinces = cls()
        for province in features(filename):
            props = province.properties
            abbreviation = cls.non_alpha.sub("", props['PRFABBR'].upper())
            place = Province(
                'state', province.geometry, id=props['PRUID'],
                name=props['PRENAME'], abbreviated_name=abbreviation,
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

class Cities(object):
    "Census divisions--basically cities and towns."

    @classmethod
    def from_directory(cls, input_dir, provinces):
        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith("_place_500k.json"):
                continue
            for place in Cities.from_file(filename, provinces):
                yield place

    
    @classmethod
    def from_file(cls, filename, provinces):
        default_parent = None
        for place in features(filename):
            props = place.properties
            # Every place in a file should be from the same province, but
            # just in case, we check every time.
            parent = default_parent
            if 'ZCTA5CE10' in props:
                # This is a ZIP code. We're going to handle these
                # separately, later.
                continue
            if 'PROVINCEFP' in props:
                province_id = props['PROVINCEFP']
                parent = provinces.by_id[province_id]
                default_parent = parent
            name = props['NAME']
            parent.saw_place_name(name)
            yield Place('city', place.geometry, props['GEOID'],
                        name, parent=parent)

canada = Nation.from_filename("ne_10m_admin_0_countries.json", "Canada")
provinces = Provinces.from_filename("gpr_000b11a_e.json", canada)
for province in provinces.by_id.values():
    print province.output

# Having gone through all the provinces, we can now make a GeoJSON
# object representing the nation as a whole.
print canada.output

for city in Cities.from_filename("gcd_000b11a_e.json", provinces):
    print city.output

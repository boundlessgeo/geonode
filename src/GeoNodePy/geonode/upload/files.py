import os.path
from geoserver.resource import FeatureType
from geoserver.resource import Coverage

from UserList import UserList
import zipfile
import os
import re


vector = FeatureType.resource_type
raster = Coverage.resource_type


xml_unsafe = re.compile(r"(^[^a-zA-Z\._]+)|([^a-zA-Z\._0-9]+)")


class SpatialFiles(UserList):

    def __init__(self, data, archive=None):
        self.data = data
        self.archive = archive

    def all_files(self):
        if self.archive:
            return [self.archive]
        all = []
        for f in self.data:
            all.extend(f.all_files())
        return all


class SpatialFile(object):

    def __init__(self, base_file, file_type, auxillary_files, 
                 sld_files):
        self.base_file = base_file
        self.file_type = file_type
        self.auxillary_files = auxillary_files
        self.sld_files = sld_files

    def all_files(self):
        return [self.base_file] + self.auxillary_files

    def __repr__(self):
        return "<SpatialFile base_file=%s file_type=%s aux=%s sld=%s>" % \
               (self.base_file, self.file_type, self.auxillary_files, self.sld_files)


class FileType(object):
    
    def __init__(self, name, code, layer_type, aliases=None, auxillary_file_exts=None):
        self.name = name
        self.code = code
        self.layer_type = layer_type
        self.auxillary_file_exts = auxillary_file_exts or []
        self.aliases = aliases or []
            
    def matches(self, ext):
        ext = ext.lower()
        return ext == self.code or ext in self.aliases
    
    def build_spatial_file(self, base, others):
        aux_files, slds = self.find_auxillary_files(base, others)
        return SpatialFile( file_type=self, base_file=base,
                            auxillary_files = aux_files, sld_files = slds )
        
    def find_auxillary_files(self, base, others):
        base_name = os.path.splitext(base)[0]
        base_matches = [ f for f in others if os.path.splitext(f)[0] == base_name ]
        slds = _find_sld_files(base_matches)
        aux_files = [ f for f in others if os.path.splitext(f)[1][1:].lower() in self.auxillary_file_exts ]
        return aux_files, slds

    def __repr__(self):
        return "<FileType %s>" % self.code


TYPE_UNKNOWN = FileType("unknown", None, None)

types = [
    FileType("Shapefile", "shp", vector, auxillary_file_exts=('dbf','shx','prj')),
    FileType("GeoTIFF", "tif", raster, aliases=('tiff','geotif','geotiff')),
    FileType("PNG", "png", raster, auxillary_file_exts=('prj',)),
    FileType("JPG", "jpg", raster, auxillary_file_exts=('prj',)),
    FileType("CSV", "csv", vector),
]


def _contains_bad_names(file_names):
    '''return True if the list of names contains a bad one'''
    xml_unsafe = re.compile(r"(^[^a-zA-Z\._]+)|([^a-zA-Z\._0-9]+)")
    return any([ xml_unsafe.search(f) for f in file_names ])


def _rename_files(file_names):
    safe_files = []
    for f in file_names:
        dirname, base_name = os.path.split(f)
        test_name = base_name
        # prefix any leading digit with an underscore to prevent a whole
        # number from getting wiped out
        if base_name[0].isdigit():
            test_name = '_%s' % base_name
        safe = xml_unsafe.sub("_", test_name)
        if safe != base_name:
            safe = os.path.join(dirname, safe)
            os.rename(f, safe)
            f = safe
        safe_files.append(f)
    return safe_files
            

def _find_sld_files(file_names):
    return [ f for f in file_names if f.lower().endswith('.sld') ]


def scan_file(file_name):
    '''get a list of SpatialFiles for the provided file'''
    dirname = os.path.dirname(file_name)
    
    files = None
    
    archive = None
    
    if zipfile.is_zipfile(file_name):
        # rename this now
        file_name = _rename_files([file_name])[0]
        zf = None
        try:
            zf = zipfile.ZipFile(file_name, 'r')
            files = zf.namelist()
            if _contains_bad_names(files):
                zf.extractall(dirname)
                files = None
            else:
                archive = os.path.abspath(file_name)
                for f in _find_sld_files(files):
                    zf.extract(f, dirname)
        except:
            raise Exception('Unable to read zip file')
        zf.close()

    def dir_files():
        abs = lambda *p : os.path.abspath(os.path.join(*p))
        return [abs(dirname, f) for f in os.listdir(dirname)]

    if files is None:
        # not a zip, list the files
        files = dir_files()
    else:
        # is a zip, add other files (sld if any)
        files.extend(dir_files())

    files = _rename_files(files)
    
    found = []
    
    for file_type in types:
        for f in files:
            name, ext = os.path.splitext(f)
            if file_type.matches(ext[1:]):
                found.append( file_type.build_spatial_file(f, files) )

    # detect slds and assign iff a single upload is found
    sld_files = _find_sld_files(files)
    if sld_files:
        if len(found) == 1:
            found[0].sld_files = sld_files
        else:
            raise Exception("One or more SLD files was provided, but no " +
                            "matching files were found for them.")
                
    return SpatialFiles(found, archive)

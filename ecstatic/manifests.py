from django.conf import settings
from django.utils import simplejson as json
from django.utils.functional import LazyObject
from django.utils.importlib import import_module


class JsonManifest(object):
    _cleared = False
    _data = {}

    def clear(self):
        self._cleared = True
        self._data = {}

    def add(self, key, value):
        self._data[key] = value

    def flush(self):
        file = open(settings.ECSTATIC_MANIFEST_FILE, mode='w+')
        data = {}

        if not self._cleared:
            # Load the existing data from the file
            is_empty = file.read(1) is None
            file.seek(0)
            if not is_empty:
                data = json.load(file)

        self._data.update(data)
        json.dump(self._data, file, indent=4)
        file.truncate()
        file.close()
        self._data = {}
        self._cleared = False


class ConfiguredStaticFilesManifest(LazyObject):
    def _setup(self):
        self._wrapped = get_manifest_class(settings.ECSTATIC_MANIFEST)()


def get_manifest_class(import_path=None):
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a manifest module." % import_path)
    module, classname = import_path[:dot], import_path[dot+1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing manifest module %s: "%s"' % (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Manifest module "%s" does not define a "%s" class.' % (module, classname))


static_files_manifest = ConfiguredStaticFilesManifest()

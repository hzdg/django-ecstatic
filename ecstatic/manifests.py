from django.conf import settings
from django.core.cache import get_cache
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject
from django.utils.importlib import import_module
import os
import json


class NotInManifest(Exception):
    pass


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

    def _get_cache_key(self, name, manifest_mtime):
        return 'ecstatic:staticmanifest:%s:%s' % (manifest_mtime, name)

    def get(self, key):
        manifest_mtime = os.path.getmtime(settings.ECSTATIC_MANIFEST_FILE)
        cache_key = self._get_cache_key(key, manifest_mtime)
        cache = get_cache(settings.ECSTATIC_MANIFEST_CACHE)
        value = cache.get(cache_key)
        if value is None:
            # Populate the cache with the entire contents of the manifest.
            # The manifest should fit in the cache, so this will reduce the
            # number of times we need to read the file.
            file = open(settings.ECSTATIC_MANIFEST_FILE)
            data = json.load(file)
            for name, url in data.items():
                cache.set(self._get_cache_key(name, manifest_mtime), url)
                if name == key:
                    value = url
        if value is None:
            raise NotInManifest('The file "%s" was not found in the'
                                ' manifest.' % key)
        return value


class ConfiguredStaticFilesManifest(LazyObject):
    def _setup(self):
        self._wrapped = get_manifest_class(settings.ECSTATIC_MANIFEST)()


def get_manifest_class(import_path=None):
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a manifest module." % import_path)
    module, classname = import_path[:dot], import_path[dot + 1:]
    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing manifest module %s: "%s"' % (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Manifest module "%s" does not define a "%s" class.' % (module, classname))


staticfiles_manifest = ConfiguredStaticFilesManifest()

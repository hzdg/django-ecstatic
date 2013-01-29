from contextlib import contextmanager
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import (StaticFilesStorage,
        CachedFilesMixin as _CachedFilesMixin)
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from fnmatch import fnmatch
import itertools
import os
import types
from .manifests import staticfiles_manifest
from .utils import get_hashed_filename, split_filename


@contextmanager
def patched_name_fn(storage, fn_name, desc):
    original_fn = getattr(storage, fn_name)

    def patched(self, name, *args, **kwargs):
        try:
            return original_fn(name, *args, **kwargs)
        except Exception, exc:
            if self.strict:
                raise

            # TODO: Real warning?
            print ('WARNING: Could not get %s for "%s". Using "%s" instead.'
                   ' To change this behavior, set your storage\'s `strict`'
                   ' attribute to `False`. Error was: %s'
                   % (desc, name, name, exc))
            # Increment error count.
            setattr(self, '_post_process_error_count',
                    getattr(self, '_post_process_error_count', 0))
            self._post_process_error_count += 1
            return name

    method = types.MethodType(patched, storage)
    setattr(storage, fn_name, method)

    yield

    setattr(storage, fn_name, original_fn)


@contextmanager
def post_process_error_counter(storage):
    storage._post_process_error_count = 0
    yield
    storage._post_process_error_count = 0


class LaxPostProcessorMixin(object):
    strict = settings.ECSTATIC_STRICT

    def post_process(self, paths, dry_run=False, **options):
        """
        Overridden to work around https://code.djangoproject.com/ticket/19111
        """
        with post_process_error_counter(self):
            with patched_name_fn(self, 'hashed_name', 'hashed name'):
                with patched_name_fn(self, 'url', 'url'):
                    for result in super(LaxPostProcessorMixin,
                                        self).post_process(paths, dry_run, **options):
                        yield result
            error_count = self._post_process_error_count
            print '\n%s post-processing error%s.' % (error_count,
                    '' if error_count == 1 else 's')


class BuiltFileStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.ECSTATIC_BUILD_ROOT
            if not location:
                raise ImproperlyConfigured('ECSTATIC_BUILD_ROOT must be set.')
        if base_url is None:
            base_url = settings.STATIC_URL
        super(BuiltFileStorage, self).__init__(location, base_url,
                                               *args, **kwargs)

    def find(self, path, all=False):
        if settings.ECSTATIC_COLLECT_BUILT:
            return super(BuiltFileStorage, self).find(path, all)
        else:
            return []

    def listdir(self, path):
        if settings.ECSTATIC_COLLECT_BUILT:
            return super(BuiltFileStorage, self).listdir(path)
        else:
            return [], []


class CachedFilesMixin(LaxPostProcessorMixin, _CachedFilesMixin):
    """
    A subclass of ``django.contrib.staticfiles.storage.CachedFilesMixin`` that
    allows you to exclude files from postprocessing.

    """
    postprocess_exclusions = []

    def exclude_file(self, name):
        return any(fnmatch(name, pattern) for pattern in
                self.postprocess_exclusions)

    def hashed_name(self, name, content=None):
        if not self.exclude_file(name):
            name = super(CachedFilesMixin, self).hashed_name(name, content)
        return name

    def post_process(self, paths, dry_run=False, **options):
        """
        Overridden to allow some files to be excluded (using
        ``postprocess_exclusions``)

        """
        if self.postprocess_exclusions:
            paths = dict((k, v) for k, v in paths.items() if not
                    self.exclude_file(k))
        return super(CachedFilesMixin, self).post_process(paths,
                dry_run, **options)


class CachedStaticFilesMixin(CachedFilesMixin):
    """
    A mixin that uses the local version of the static file to compute the hash.
    This removes at least one network connection when using a remote storage
    (``CachedFilesMixin.hashed_name``'s checks for existence and opening of the
    file) but adds the requirement that the static files be locally accessible
    (which they should be already).

    """
    def hashed_name(self, name, content=None):
        if content is None:
            path = finders.find(name)

            if path:
                # Really, we should be using the associated storage object to open
                # the file, but Django doesn't seem to expose that, so we just
                # assume it's a file on the local filesystem.
                content = File(open(path))
            else:
                raise ValueError('No static file name "%s" exists.' % name)

        return super(CachedStaticFilesMixin, self).hashed_name(name, content)


class CachedStaticFilesStorage(CachedFilesMixin, StaticFilesStorage):
    """
    A static file system storage backend which also saves
    hashed copies of the files it saves.
    """
    pass


# FIXME: extract a mixin
class HashedNameFileSystemStorage(FileSystemStorage):
    def get_available_name(self, name):
        dir_name, filename = os.path.split(name)
        basename, hash, ext = split_filename(filename)

        count = itertools.count(1)
        while self.exists(name):
            name = os.path.join(dir_name, '%s_%s%s%s' % (basename, count.next(),
                                                         hash, ext))

        return name

    def save(self, name, content):
        name = get_hashed_filename(name, content)
        return super(HashedNameFileSystemStorage, self).save(name, content)


class StaticManifestMixin(object):
    def generate_url(self, name):
        return super(StaticManifestMixin, self).url(name, force=True)

    def url(self, name, force=False):
        if not settings.ECSTATIC_USE_MANIFEST and not force:
            return super(StaticManifestMixin, self).url(name, force)

        return staticfiles_manifest.get(name)

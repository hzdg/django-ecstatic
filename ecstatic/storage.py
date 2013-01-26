from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import (StaticFilesStorage,
        CachedFilesMixin as _CachedFilesMixin)
from django.contrib.staticfiles.utils import matches_patterns
from django.core.cache import (get_cache, InvalidCacheBackendError,
                               cache as default_cache)
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_text, smart_bytes
from fnmatch import fnmatch
import itertools
import os
import posixpath
import re
try:
    from urllib.parse import unquote
except ImportError:     # Python 2
    from urllib import unquote
from .manifests import staticfiles_manifest
from .utils import get_hashed_filename, split_filename


class BuiltFileStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.ECSTATIC_BUILD_ROOT
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


class BaseCachedFilesMixin(_CachedFilesMixin):
    """
    This class has a few purposes:

    1. Fixes https://code.djangoproject.com/ticket/19670#ticket
    2. Allows for custom url_converter-like methods
    3. Provides a non-strict mode that won't fail when it fails to convert
       urls. Be careful, though, being able to use paths that don't exist is a
       double-edged sword!

    Unfortunately, the superclass
    (``django.contrib.staticfiles.storage.CachedFileMixins``) isn't very easy to
    extend, so most of this class is just a copy-paste job from Django. /:

    """
    strict = False
    default_template = """url("%s")"""
    patterns = (
        ('*.css', (
            """(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""",
            (r"""(@import\s*["']\s*(.*?)["'])""", """@import url("%s")"""),
        )),
    )

    def __init__(self, *args, **kwargs):
        super(_CachedFilesMixin, self).__init__(*args, **kwargs)
        try:
            self.cache = get_cache('staticfiles')
        except InvalidCacheBackendError:
            # Use the default backend
            self.cache = default_cache
        self._patterns = SortedDict()
        for extension, patterns in self.patterns:
            for pattern in patterns:

#
# A small difference from Django here: we allow a
# three-tuple where the final item is the name of a method
# on this object that will create the converter function.
#

                converter_factory = 'url_converter'
                if isinstance(pattern, (tuple, list)):
                    if len(pattern) == 2:
                        pattern, template = pattern
                    elif len(pattern) == 3:
                        pattern, template, converter_factory = pattern
                    else:
                        raise Exception
                else:
                    template = self.default_template
                compiled = re.compile(pattern)
                self._patterns.setdefault(extension, []).append((compiled, template, converter_factory))

#
#
#

    def url_converter(self, name, template=None):
        """
        Returns the custom URL converter for the given file name.
        """
        if template is None:
            template = self.default_template

        def converter(matchobj):
            """
            Converts the matched URL depending on the parent level (`..`)
            and returns the normalized and hashed URL using the url method
            of the storage.
            """
            matched, url = matchobj.groups()
            # Completely ignore http(s) prefixed URLs,
            # fragments and data-uri URLs
            if url.startswith(('#', 'http:', 'https:', 'data:', '//')):
                return matched
            name_parts = name.split(os.sep)
            # Using posix normpath here to remove duplicates
            url = posixpath.normpath(url)
            url_parts = url.split('/')
            parent_level, sub_level = url.count('..'), url.count('/')
            if url.startswith('/'):
                sub_level -= 1
                url_parts = url_parts[1:]
            if parent_level or not url.startswith('/'):
                start, end = parent_level + 1, parent_level
            else:
                if sub_level:
                    if sub_level == 1:
                        parent_level -= 1
                    start, end = parent_level, 1
                else:
                    start, end = 1, sub_level - 1
            joined_result = '/'.join(name_parts[:-start] + url_parts[end:])
            hashed_url = self.url(unquote(joined_result), force=True)
            file_name = hashed_url.split('/')[-1:]
            relative_url = '/'.join(url.split('/')[:-1] + file_name)

            # Return the hashed version to the file
            return template % unquote(relative_url)

        return converter

    def post_process(self, paths, dry_run=False, **options):
        # don't even dare to process the files if we're in dry run mode
        if dry_run:
            return

        # where to store the new paths
        hashed_paths = {}

        # build a list of adjustable files
        matches = lambda path: matches_patterns(path, self._patterns.keys())
        adjustable_paths = [path for path in paths if matches(path)]

        # then sort the files by the directory level
        path_level = lambda name: len(name.split(os.sep))
        for name in sorted(paths.keys(), key=path_level, reverse=True):

            # use the original, local file, not the copied-but-unprocessed
            # file, which might be somewhere far away, like S3
            storage, path = paths[name]
            with storage.open(path) as original_file:

                # generate the hash with the original content, even for
                # adjustable files.
                hashed_name = self.hashed_name(name, original_file)

                # then get the original's file content..
                if hasattr(original_file, 'seek'):
                    original_file.seek(0)

                hashed_file_exists = self.exists(hashed_name)
                processed = False

                # ..to apply each replacement pattern to the content
                if name in adjustable_paths:
                    content = original_file.read().decode(settings.FILE_CHARSET)

#
# Here's the part we're changing. We use `matches_pattern`
# (instead of fnmatch) in case the implementation changes
# to maintain consistency, even though we only have a single
# pattern.
#

                    for extension, patterns in self._patterns.items():
                        if matches_patterns(name, [extension]):
                            for pattern, template, converter_factory in patterns:
                                factory = getattr(self, converter_factory)
                                converter = factory(name, template)
                                if not self.strict:
                                    converter = self._wrap_converter(converter, name, template)
                                content = pattern.sub(converter, content)

#
#
#

                    if hashed_file_exists:
                        self.delete(hashed_name)
                    # then save the processed result
                    content_file = ContentFile(smart_bytes(content))
                    saved_name = self._save(hashed_name, content_file)
                    hashed_name = force_text(saved_name.replace('\\', '/'))
                    processed = True
                else:
                    # or handle the case in which neither processing nor
                    # a change to the original file happened
                    if not hashed_file_exists:
                        processed = True
                        saved_name = self._save(hashed_name, original_file)
                        hashed_name = force_text(saved_name.replace('\\', '/'))

                # and then set the cache accordingly
                hashed_paths[self.cache_key(name.replace('\\', '/'))] = hashed_name
                yield name, hashed_name, processed

        # Finally set the cache
        self.cache.set_many(hashed_paths)

    def _wrap_converter(self, converter, name, template):
        """
        Wraps a converter to make it tolerant of errors. If the wrapped
        converter raises an Exception, the original URL will be used.

        """
        def wrapper(matchobj):
            matched, url = matchobj.groups()
            try:
                return converter(matchobj)
            except Exception, exc:
                # TODO: Use logger?
                print 'WARNING: Could not convert "%s" in file "%s": %s' % (url, name, exc)
                return template % url

        return wrapper


class CachedFilesMixin(BaseCachedFilesMixin):
    """
    A subclass of ``django.contrib.staticfiles.storage.CachedFilesMixin`` that
    allows you to exclude files from postprocessing.

    """
    postprocess_exclusions = []
    strict = False

    def exclude_file(self, name):
        return any(fnmatch(name, pattern) for pattern in
                self.postprocess_exclusions)

    def hashed_name(self, name, content=None):
        """
        Overridden to work around https://code.djangoproject.com/ticket/19111
        """
        if not self.exclude_file(name):
            try:
                name = super(CachedFilesMixin, self).hashed_name(name, content)
            except ValueError:
                if self.strict:
                    raise
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
            elif self.strict:
                raise ValueError('No static file name "%s" exists.' % name)
            else:
                return name

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


class JsStaticMacroMixin(object):
    def __init__(self, *args, **kwargs):
        if '*.js' not in dict(self.patterns):
            self.patterns += ((
                '*.js', (
                    (
                        r"""(%s\(\s*['"](.*?)["']\s*\))""" % re.escape(settings.ECSTATIC_JS_STATIC_MACRO),
                        "'%s'",
                        'js_static_macro_converter',
                    ),
                )
            ),)
        super(JsStaticMacroMixin, self).__init__(*args, **kwargs)

    def js_static_macro_converter(self, name, template=None):
        """
        Like url_converter, but simply uses the storage class's url method to
        perform the conversion. Perfect for doing "{% static x %}"-like macro
        expansions.

        """
        if template is None:
            template = self.default_template

        def converter(matchobj):
            matched, url = matchobj.groups()
            return template % self.url(url)

        return converter

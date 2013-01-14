from django.contrib.staticfiles.storage import (
        CachedFilesMixin as _CachedFilesMixin)
from django.core.files.storage import FileSystemStorage
from fnmatch import fnmatch
import itertools
import os
from .utils import get_hashed_filename, split_filename


class CachedFilesMixin(_CachedFilesMixin):
    """
    A subclass of ``django.contrib.staticfiles.storage.CachedFilesMixin`` that
    allows you to exclude files from postprocessing.

    """
    save_without_hash = True
    save_with_hash = True
    postprocess_exclusions = []

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
                pass
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

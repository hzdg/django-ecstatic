import os
import sys

from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStatic
from django.core.management.base import CommandError
from django.contrib.staticfiles import finders
from django.utils.datastructures import SortedDict
from hashlib import md5
from optparse import make_option
from ..utils import StorageOverrideMixin


class CollectNewMixin(object):

    comparison_method_aliases = {
        'md5': 'file_hash',
        'mtime': 'modified_time',
    }

    def __init__(self, *args, **kwargs):
        self.option_list = list(self.option_list) + [
            make_option('--compare', default='modified_time',
                dest='comparison_method',
                help='The comparison method to use in order to determine which'
                    ' file is newer. Options are modified_time/mtime and'
                    ' file_hash/md5. Note that, with file_hash, the file will'
                    ' be opened if the storage does not define a file_hash'
                    ' method, so you should define a file_hash method for'
                    ' remote storage backends (or avoid the file_hash'
                    ' comparison method). The modified_time method must return'
                    ' a local datetime; file_hash must return an md5'
                    ' hexdigest.'),
            make_option('--immediate', default=False,
                action='store_true', dest='Immediate_post_process',
                help='The default behavior of collectstatic is to collect'
                    ' the files first then batch post-process them.'
                    ' The Immediate flag will post-process each individual'
                    ' file after it\'s collected')
        ]
        super(CollectNewMixin, self).__init__(*args, **kwargs)

    def collect(self):
        """
        Perform the bulk of the work of collectstatic.

        Split off from handle_noargs() to facilitate testing.
        """
        if self.symlink:
            if sys.platform == 'win32':
                raise CommandError("Symlinking is not supported by this "
                                   "platform (%s)." % sys.platform)
            if not self.local:
                raise CommandError("Can't symlink to a remote destination.")

        if self.clear:
            self.clear_dir('')

        handler = self._get_handler()

        do_post_process = self.post_process and hasattr(self.storage, 'post_process')

        found_files = SortedDict()
        for finder in finders.get_finders():
            for path, storage in finder.list(self.ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path

                if prefixed_path not in found_files:
                    found_files[prefixed_path] = (storage, path)
                    handler(path, prefixed_path, storage)
                    if self.Immediate_post_process and do_post_process:
                        try:
                            self.post_processor(
                                    SortedDict({prefixed_path: (storage, path)}),
                                    self.dry_run)
                        except ValueError, e:
                            message = ('%s current storage requires all files'
                                ' to have been collected first. Try '
                                ' ecstatic.storage.CachedStaticFilesStorage' \
                                % e)
                            raise ValueError(message)

        if not self.Immediate_post_process and do_post_process:
            self.post_processor(found_files, self.dry_run)

        return {
            'modified': self.copied_files + self.symlinked_files,
            'unmodified': self.unmodified_files,
            'post_processed': self.post_processed_files,
        }

    def set_options(self, **options):
        super(CollectNewMixin, self).set_options(**options)
        comparison_method = options.get('comparison_method')
        self.comparison_method = self.comparison_method_aliases.get(comparison_method, comparison_method)
        self.Immediate_post_process = options.get('Immediate_post_process')

    def delete_file(self, path, prefixed_path, source_storage):
        if self.comparison_method == 'modified_time':
            return CollectStatic.delete_file(self, path, prefixed_path, source_storage)
        elif self.storage.exists(prefixed_path):
            should_delete = self.compare(path, prefixed_path, source_storage)
            if should_delete:
                if self.dry_run:
                    self.log(u"Pretending to delete '%s'" % path)
                else:
                    self.log(u"Deleting '%s'" % path)
                    self.storage.delete(prefixed_path)
            else:
                self.log(u"Skipping '%s' (not modified)" % path)
                return False
        return True

    def compare(self, path, prefixed_path, source_storage):
        """
        Returns True if the file should be copied.
        """
        # First try a method on the command named compare_<comparison_method>
        # If that doesn't exist, create a comparitor that calls methods on the
        # storage with the name <comparison_method>, passing them the name.
        comparitor = getattr(self, 'compare_%s' % self.comparison_method, None)
        if not comparitor:
            comparitor = self._create_comparitor(self.comparison_method)
        return comparitor(path, prefixed_path, source_storage)

    def _create_comparitor(self, comparison_method):
        def comparitor(path, prefixed_path, source_storage):
            # If both storage objects don't implement a method with a name that
            # matches the comparison method, this will raise an exception.
            source_fn = getattr(source_storage, comparison_method)
            dest_fn = getattr(self.storage, comparison_method)
            source_value = source_fn(path)
            dest_value = dest_fn(path)
            return source_value == dest_value
        return comparitor

    def compare_file_hash(self, path, prefixed_path, source_storage):
        old_md5 = self._get_md5(self.storage, path)
        new_md5 = self._get_md5(source_storage, prefixed_path)
        return old_md5 != new_md5

    def _get_md5(self, storage, name):
        fn = getattr(storage, 'file_hash', None)
        if fn:
            return fn(name)
        else:
            file = storage.open(name)
            contents = file.read()
            return md5(contents).hexdigest()

    def post_processor(self, found_files, dry_run):
        processor = self.storage.post_process(found_files, dry_run=dry_run)
        for original_path, processed_path, processed in processor:
            if processed:
                self.log(u"Post-processed '%s' as '%s" %
                         (original_path, processed_path), level=1)
                self.post_processed_files.append(original_path)
            else:
                self.log(u"Skipped post-processing '%s'" % original_path)

    def _get_handler(self):
        return self.link_file if self.symlink else self.copy_file


class Command(StorageOverrideMixin, CollectNewMixin, CollectStatic):
    """
    A version of Django's ``collectstatic`` with some useful extra options. For
    example, you can choose to only collect new files (which is great for
    collecting to a CDN).

    """
    pass

from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStatic
from hashlib import md5
from optparse import make_option


class CollectNewMixin(object):

    comparison_method_aliases = {
        'md5': 'file_hash',
        'mtime': 'modified_time',
    }

    def __init__(self, *args, **kwargs):
        self.option_list = list(self.option_list) + [
            make_option('--compare', default='modified_time',
                dest='comparison_method',
                help='The comparison method to use in order to determine which file'
                    ' is newer. Options are modified_time/mtime and file_hash/md5. Note that,'
                    ' with file_hash, the file will be opened if the storage does'
                    ' not define a file_hash method, so you should define a'
                    ' file_hash method for remote storage backends (or avoid the'
                    ' file_hash comparison method). The modified_time method must'
                    ' return a local datetime; file_hash must return an md5'
                    ' hexdigest.')
        ]
        super(CollectNewMixin, self).__init__(*args, **kwargs)

    def set_options(self, **options):
        super(CollectNewMixin, self).set_options(**options)
        comparison_method = options.get('comparison_method')
        self.comparison_method = self.comparison_method_aliases.get(comparison_method, comparison_method)

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


class Command(CollectNewMixin, CollectStatic):
    """
    A version of Django's ``collectstatic`` with some useful extra options. For
    example, you can choose to only collect new files (which is great for
    collecting to a CDN).

    """
    pass

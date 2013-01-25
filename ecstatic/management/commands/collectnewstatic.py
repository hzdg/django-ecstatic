from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStatic
from hashlib import md5
from optparse import make_option


class Command(CollectStatic):

    option_list = CollectStatic.option_list + (
        make_option('--compare', default='modified_time',
            dest='comparison_method',
            help='The comparison method to use in order to determine which file'
                ' is newer. Options are modified_time and file_hash. Note that,'
                ' with file_hash, the file will be opened if the storage does'
                ' not define a file_hash method, so you should define a'
                ' file_hash method for remote storage backends (or avoid the'
                ' file_hash comparison method).'),
    )

    def link_file(self, path, prefixed_path, source_storage):
        self._if_modified(path, prefixed_path, source_storage,
                          super(Command, self).link_file)

    def copy_file(self, path, prefixed_path, source_storage):
        self._if_modified(path, prefixed_path, source_storage,
                          super(Command, self).copy_file)

    def _if_modified(self, path, prefixed_path, source_storage, handler):
        if self.storage.exists(path):
            if not self.compare(path, prefixed_path, source_storage):
                self.log(u'Skipping %s' % path)
                return
        handler(path, prefixed_path, source_storage)

    def compare(self, path, prefixed_path, source_storage):
        """
        Returns True if the file should be copied.
        """
        comparitor = getattr(self, 'compare_%s' % self.comparison_method)
        return comparitor(path, prefixed_path, source_storage)

    def set_options(self, **options):
        super(Command, self).set_options(**options)
        self.comparison_method = options.get('comparison_method')

    def compare_modified_time(self, path, prefixed_path, source_storage):
        old_mtime = self.storage.modified_time(path)
        if old_mtime:
            new_mtime = source_storage.modified_time(prefixed_path)
            if new_mtime < old_mtime:
                return False
        return True

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

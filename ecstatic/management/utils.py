from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import get_storage_class
from optparse import make_option


class StorageOverrideMixin(object):
    def __init__(self, *args, **kwargs):
        self.option_list = self.option_list + (
            make_option('-s', '--storage', action='store',
                dest='storage_override', type="string",
                help='override default storage backend'),
        )
        super(StorageOverrideMixin, self).__init__(*args, **kwargs)

    def set_options(self, **options):
        try:
            super_set_options = super(StorageOverrideMixin, self).set_options
        except AttributeError:
            pass
        else:
            super_set_options(**options)

        storage_override = options.get('storage_override')
        if storage_override:
            cls = get_storage_class(storage_override)
            self.storage = cls()
        else:
            self.storage = staticfiles_storage

        try:
            self.storage.path('')
        except NotImplementedError:
            self.local = False
        else:
            self.local = True

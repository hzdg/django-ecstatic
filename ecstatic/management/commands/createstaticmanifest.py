from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import get_storage_class
from django.core.management.base import BaseCommand
from django.utils.datastructures import SortedDict
from optparse import make_option
import os
from ...manifests import ConfiguredStaticFilesManifest


class Command(BaseCommand):
    """
    Creates a staticfiles manifest. The exact format of the manifest is defined
    by ``ECSTATIC_MANIFEST``. By default, it's a JSON file.

    """
    option_list = BaseCommand.option_list + (
        make_option('-s', '--storage', action='store',
            dest='storage_override', type="string",
            help='override default storage backend'),
    )

    help = 'Creates a file that maps static file names to their URLs.'

    def handle(self, *args, **options):
        storage_override = options.get('storage_override')
        found_files = SortedDict()
        manifest = ConfiguredStaticFilesManifest()
        manifest.clear()

        ignore_patterns = getattr(settings, 'ECSTATIC_MANIFEST_EXCLUDES', [])

        for finder in finders.get_finders():
            for path, storage in finder.list(ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path

                if prefixed_path not in found_files:
                    found_files[prefixed_path] = path

        if storage_override:
            storage = get_storage_class(storage_override)
        else:
            storage = staticfiles_storage
        for path in found_files.values() + settings.ECSTATIC_MANIFEST_EXTRAS:
            try:
                generate_url = storage.generate_url
            except AttributeError:
                raise AttributeError('%s doesn\'t define a generate_url method.'
                        ' Did you remember to extend StaticManifestMixin?')
            hashed_name = generate_url(path)
            manifest.add(path, hashed_name)

        manifest.flush()

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import NoArgsCommand
from django.utils.datastructures import SortedDict
import os
from ..utils import StorageOverrideMixin
from ...manifests import ConfiguredStaticFilesManifest


class Command(StorageOverrideMixin, NoArgsCommand):
    """
    Creates a staticfiles manifest. The exact format of the manifest is defined
    by ``ECSTATIC_MANIFEST``. By default, it's a JSON file.

    """
    help = 'Creates a file that maps static file names to their URLs.'

    def handle_noargs(self, **options):
        self.set_options(**options)

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

        for path in found_files.values() + settings.ECSTATIC_MANIFEST_EXTRAS:
            try:
                generate_url = self.storage.generate_url
            except AttributeError:
                raise AttributeError('%s doesn\'t define a generate_url method.'
                        ' Did you remember to extend StaticManifestMixin?' %
                        self.storage)
            hashed_name = generate_url(path)
            manifest.add(path, hashed_name)

        manifest.flush()

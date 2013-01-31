from appconf import AppConf
from django.conf import settings


class EcstaticConf(AppConf):
    MANIFEST = 'ecstatic.manifests.JsonManifest'
    MANIFEST_FILE = None
    MANIFEST_EXCLUDES = ['CVS', '.*', '*~']
    MANIFEST_EXTRAS = ['admin/']
    USE_MANIFEST = not settings.DEBUG
    MANIFEST_CACHE = 'ecstatic_manifest' if 'ecstatic_manifest' in settings.CACHES else 'default'
    STRICT = False

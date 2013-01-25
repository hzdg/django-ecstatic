from appconf import AppConf
from django.conf import settings


class EcstaticConf(AppConf):
    BUILD_COMMANDS = []
    COLLECT_BUILT = True
    BUILD_INCLUDES = ['*']
    BUILD_EXCLUDES = ['CVS', '.*', '*~']
    MANIFEST = 'ecstatic.manifests.JsonManifest'
    USE_MANIFEST = not settings.DEBUG
    MANIFEST_CACHE = 'ecstatic_manifest' if 'ecstatic_manifest' in settings.CACHES else 'default'

Settings
========

.. currentmodule:: django.conf.settings


Storage Settings
----------------

.. attribute:: ECSTATIC_STRICT

    :default: ``False``

    Specifies whether Ecstatic should raise an exception when it can't convert
    a URL. If ``False``, the unconverted URL will be used. This situation
    typically arises when a CSS file points to a non-existent image.


Build Settings
--------------

.. attribute:: ECSTATIC_BUILD_COMMANDS

    :default: ``[]``

    A list of shell commands to be run by the ``buildstatic`` command.


.. attribute:: ECSTATIC_BUILD_ROOT

    :default: ``None``

    The path of the directory in which static files should be collected for
    building. You must provide a value if using ``buildstatic`` (or
    ``ecstatic.storage.BuiltFileStorage``)


.. attribute:: ECSTATIC_BUILD_INCLUDES

    :default: ``['*']``

    A list of patterns corresponding to files that should be collected for
    building.


.. attribute:: ECSTATIC_BUILD_EXCLUDES

    :default: ``['CVS', '.*', '*~']``

    A list of patterns corresponding to files that should be skipped when
    collecting for building.


Manifest Settings
-----------------

.. attribute:: ECSTATIC_MANIFEST

    :default: ``'ecstatic.manifests.JsonManifest'``

    The dotted path to the manifest class to be used by the
    ``createstaticmanifest`` management command and
    ``ecstatic.storage.StaticManifestMixin``.


.. attribute:: ECSTATIC_MANIFEST_FILE

    :default: ``None``

    The path where the manifest file should be saved. This setting must be set
    if using staticfiles manifests.


.. attribute:: ECSTATIC_USE_MANIFEST

    :default: the opposite of ``DEBUG``

    Specifies whether the manifest should be used by the
    (``ecstatic.storage.StaticManifestMixin`` extending) storage class.


.. attribute:: ECSTATIC_MANIFEST_CACHE

    :default: ``'ecstatic_manifest'``, if the ``CACHES`` dictionary contains it,
    otherwise 'default'

    The name of the cache that should be used by the manifest class.

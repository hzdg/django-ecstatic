A Quick Tour
============

django-ecstatic is an expansion pack for ``django.contrib.staticfiles``!
Read the full documentation at readthedocs__.

Here are some things it can do:

- Eliminate the need for network connections to calculate file hashes.
- Collect only the static files that have changed.
- Add a static building step to your Django workflow.
- Add content hashes to your filenames, without failing on non-existent files.
- Create static manifests to reduce network operations and ease deployment.

Ecstatic's utlities are written with the same interfaces as
``django.contrib.staticfiles``, so they should be compatible with your favorite
Django storage libraries.


__ http://django-ecstatic.readthedocs.org/
__ https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#cachedstaticfilesstorage
__ https://www.google.com/search?q=far+future+expiration
__ https://docs.djangoproject.com/en/dev/ref/settings/#staticfiles-storage



Hashed Filenames FTW
--------------------

First of all, you should already be using Django's CachedFilesMixin or
CachedStaticFilesStorage__ classes, which add a post-processing step to the
`collectstatic` command that saves a copy of your static files with a hash of
their contents in the filename. If you're serving the files yourself, this will
allow you to set `far-future expirations`__ for your assets, which will make
your site's users happy. It also means that new versions of assets won't
overwrite the old versions, which would break your site if the deployed code and
static files aren't in sync.

However, in order to get the content hash, these classes will open the file
using your app's STATICFILES_STORAGE__. If you're using a CDN, this means
they'll be performing network operations. But those static files are saved on
the local filesystem, too—after all, they were collected from somewhere. That's
where ``ecstatic.storage.CachedStaticFilesMixin`` and
``ecstatic.storage.CachedStaticFilesStorage`` come in. Instead of using the
storage class to get the hash, they'll use your app's staticfiles finders to
find the local version and use its hash. (They also have a couple of other handy
features.) Use the mixin with the storage class of your choice to get the
benefits:

.. code-block:: python

    from ecstatic.storage import CachedStaticFilesMixin
    from cumulus.storage import CloudFilesStaticStorage


    class MyStaticFilesStorage(CachedStaticFilesMixin, CloudFilesStaticStorage):
        pass


Building Static Files
---------------------

Sooner or later, you're going to need to add a build step to your Django apps;
whether it's because of Sass_, Less_, Coffee_, AMD_, or just to optimize your
PNGs and JPEGs. There are a few__ popular__ ways to do some of these things with
Django, but each has its own specific goals, and you can easily find your build
requirements outside of their scope. Ecstatic takes a different approach by
giving you a simple way to add a build step to your workflow, but has absolutely
no opinion about what that build step should be, making it easy to take
advantage of whatever build tools you want.

The heart of the Ecstatic build step is the ``buildstatic`` management command,
and it is stupid simple. In fact, it only does two things: first, it collects
your static files into a build directory and, second, it runs some shell
commands. (Seriously, look at `the source`__. It delegates most of its work to
Django's ``collectstatic``. And that's A Good Thing.)

To specify the build directory, use the ``ECSTATIC_BUILD_ROOT`` setting:

.. code-block:: python

    ECSTATIC_BUILD_ROOT = os.path.join(os.path.dirname(__file__), 'static_built')

To specify a list of shell commands to run with the ``ECSTATIC_BUILD_COMMANDS``
setting:

.. code-block:: python

    ECSTATIC_BUILD_COMMANDS = [
        'coffee -c /path/to/build_dir',
        'uglifyjs /path/to/build_dir/a.js -c > /path/to/build_dir/a.js',
    ]

or (to keep things a little more tidy):

.. code-block:: python

    ECSTATIC_BUILD_COMMANDS = ['./bin/mybuildscript']

Finally, you'll need to add a special finder to your ``STATICFILES_FINDERS``
list:

.. code-block:: python

    STATICFILES_FINDERS = (
        'ecstatic.finders.BuiltFileFinder',

        # The default Django finders:
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    )

This finder is important—it's how Django finds the built versions of your files
when you run ``collectstatic``.


.. _Sass: http://sass-lang.com/
.. _Less: http://lesscss.org/
.. _Coffee: http://coffeescript.org/
.. _AMD: http://requirejs.org/docs/whyamd.html
__ https://github.com/jezdez/django_compressor
__ https://github.com/cyberdelia/django-pipeline
__ https://github.com/hzdg/django-ecstatic/blob/master/ecstatic/management/commands/buildstatic.py




Hashed Filenames and Built Files
--------------------------------

Remember when I mentioned how ``ecstatic.storage.CachedStaticFilesMixin`` and
``ecstatic.storage.CachedStaticFilesStorage`` worked? They calculate the hashes
of the local versions of the static files. Obviously, then, the local
versions—that is, the static files on your app server—need to be the same as the
ones you collected to your CDN. Otherwise, the app server would get different
hashes and use the wrong URL! So if you're building your static files, you need
to make sure that the built files are on your app server. There are two ways
to do this:

1. Include your ``STATIC_BUILD`` directory in your package and deploy it with
   the rest of your application code.
2. Re-build the static files on the app server.

Alternatively, you can go back to using
``django.contrib.staticfiles.storage.CachedFilesMixin`` or
``django.contrib.staticfiles.storage.CachedStaticFilesStorage``, though then
you're back in the situation of using network operations to get the hash.

All of the above options have pros and cons. If you deploy directly from
version control, option 1 would mean committing compiled files to your
repository, which you may consider bloat. On the other hand, option 2 means that
your app server needs to have all of your build tools installed. It also means
that there will be some time while new code is deployed, but it's referencing
old assets (until the build completes so the storage can get the new hash).

Luckily, Ecstatic has another solution:
``ecstatic.storage.StaticManifestMixin``. This mixin is used just like
``ecstatic.storage.CachedStaticFilesMixin``, but it looks up your static files
URLs in a manifest file—completely sidestepping the need to calculate the hash
of the local files.

.. code-block:: python

    from ecstatic.storage import CachedStaticFilesMixin, StaticManifestMixin
    from cumulus.storage import CloudFilesStaticStorage


    class MyStaticFilesStorage(StaticManifestMixin, CachedStaticFilesMixin, CloudFilesStaticStorage):
        pass

.. note::

    Notice that we're still including ``CachedStaticFilesMixin``. It's still
    needed for the post-processing, and to figure out which URL should be
    inserted into the manifest.

With this mixin, the storage no longer needs access to the built files to
determine their hashes (and therefore URLs); it only needs to access the
manifest file. That means:

- You don't need to package your built static files with your app.
- You don't need to install your build tools on your app server.
- The storage class can lookup the new URL as soon as new code is deployed
  (along with a new staticfiles manifest).
- We still aren't performing network operations to get hashes/URLs.

In other words, we've solved all of our issues. Yay!

So how do you create this manifest? First, you need to add a variable to your
settings.py file to let Ecstatic know where to create it:

.. code-block:: python

    ECSTATIC_MANIFEST_FILE = os.path.join(os.path.dirname(__file__), 'staticmanifest.json')

Then just run the ``createstaticmanifest`` management command:

.. code-block:: sh

    ./manage.py createstaticmanifest

.. note::

    When you run ``createstaticmanifest``, make sure that the Django settings
    you're using contain the correct ``STATICFILES_STORAGE``. If you have a
    local_settings.py that sets a different ``STATICFILES_STORAGE``, the
    manifest will contain the URLs that it reports!

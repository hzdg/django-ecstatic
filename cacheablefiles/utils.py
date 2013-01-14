from hashlib import md5
import re


hashed_filename_pattern = r"""
    (?P<name>.+?)                  # A basename that's at least 1 char long
    (
        (?P<hash>\.[a-f0-9]{12})?  # A 12-character hexidecimal hash, only matched if an extension is also found
        (?P<ext>\.[^\.]+)          # An extension
    )?                             # The hash and extension are optional
    $                              # The end of the string
    """

hashed_filename_re = re.compile(hashed_filename_pattern, re.VERBOSE)


def get_hashed_filename(name, file, suffix=None):
    """
    Gets a new filename for the provided file of the form
    "oldfilename.hash.ext". If the old filename looks like it already contains a
    hash, it will be replaced (so you don't end up with names like
    "pic.hash.hash.ext")

    """
    basename, hash, ext = split_filename(name)
    file.seek(0)
    new_hash = '.%s' % md5(file.read()).hexdigest()[:12]
    if suffix is not None:
        basename = '%s_%s' % (basename, suffix)
    return '%s%s%s' % (basename, new_hash, ext)


def split_filename(name):
    """
    Splits the filename into three parts: the name part, the hash part, and the
    extension. Like with the extension, the hash part starts with a dot.

    """
    parts = hashed_filename_re.match(name).groupdict()
    return (parts['name'] or '', parts['hash'] or '', parts['ext'] or '')

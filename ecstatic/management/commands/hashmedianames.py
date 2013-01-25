from django.core.management.base import BaseCommand
from django.db.models import get_models
from django.db.models.fields.files import ImageField, FileField
import os
from ...utils import get_hashed_filename


class Command(BaseCommand):
    help = 'Renames existing media files to include a hash of their contents.'

    def handle(self, *args, **options):
        for model in get_models():
            # See if the model has any ImageFields or FileFields
            # TODO: Add setting for field types
            field_names = [f.name for f in model._meta.fields if type(f) in
                    (ImageField, FileField)]

            if field_names:
                print 'Hashing filenames for %s.%s...' % (model._meta.app_label,
                                          model._meta.object_name)

                for m in model.objects.all():
                    updated = False
                    for field_name in field_names:
                        updated = updated or self.rename_file(m, field_name)
                    if updated:
                        m.save()

    def rename_file(self, instance, field_name):
        """
        Renames a file and updates the model field to point to the new file.
        Returns True if a change has been made; otherwise False

        """
        file = getattr(instance, field_name)

        if file:
            new_name = get_hashed_filename(file.name, file)
            if new_name != file.name:
                print '    Renaming "%s" to "%s"' % (file.name, new_name)
                file.save(os.path.basename(new_name), file, save=False)
                return True

        return False

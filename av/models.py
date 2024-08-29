# oppia/av/models.py
import os
from shutil import copyfile

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UploadedMedia(models.Model):

    create_user = models.ForeignKey(User,
                                    related_name='media_create_user',
                                    null=True,
                                    on_delete=models.SET_NULL)
    update_user = models.ForeignKey(User,
                                    related_name='media_update_user',
                                    null=True,
                                    on_delete=models.SET_NULL)
    created_date = models.DateTimeField('date created',
                                        default=timezone.now)
    lastupdated_date = models.DateTimeField('date updated',
                                            default=timezone.now)
    file = models.FileField(upload_to="uploaded/%Y/%m/", blank=False)
    md5 = models.CharField(max_length=100)
    length = models.IntegerField(default=0, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    organisation = models.CharField(max_length=200, blank=True, null=True)
    license = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _(u'Uploaded Media')
        verbose_name_plural = _(u'Uploaded Media')

    def __str__(self):
        return self.file.name

    def filename(self):
        return os.path.basename(self.file.name)

    def get_filesize(self):
        try:
            return self.file.size
        except FileNotFoundError:
            return 0

@receiver(post_save, sender=UploadedMedia)
def uploaded_media_save_to_external(sender, instance, **kwargs):
    if settings.OPPIA_EXTERNAL_STORAGE:
        copy_from = os.path.join(settings.MEDIA_ROOT, instance.file.name)
        copy_to = os.path.join(settings.OPPIA_EXTERNAL_STORAGE_MEDIA_ROOT, instance.filename())
        copyfile(copy_from, copy_to)


@receiver(post_delete, sender=UploadedMedia)
def uploaded_media_delete_file(sender, instance, **kwargs):
    file_to_delete = os.path.join(settings.MEDIA_ROOT, instance.file.name)
    try:
        os.remove(file_to_delete)
    except OSError:
        pass

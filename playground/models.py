from django.db import models
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class UserProfile(models.Model):
    email = models.EmailField(max_length=200)
    camera = models.IntegerField()
    alert_on = models.BooleanField(default=False)
    path = models.FilePathField(path=str(BASE_DIR), allow_folders=True,
                                allow_files=False, recursive=True)

    def __str__(self):
        return self.email

class Recording(models.Model):
    name = models.TextField()
    date = models.TextField()
    time = models.TextField()
    description = models.TextField()
    file = models.FileField()

    def __str__(self):
        return self.name
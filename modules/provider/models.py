from django.db import models
import uuid
from modules.user.models import User
from django.utils import timezone


class TypeId(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "type_id"


class Provider(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.CharField(max_length=100)  
    fullname = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20)
    rnt = models.CharField(max_length=10)
    address = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    id_type = models.ForeignKey(TypeId, on_delete=models.PROTECT, null=True)
    created_date = models.DateTimeField('date created', default=timezone.now)

    def __str__(self):
        return str(self.user)

    class Meta:
        db_table = "provider"
        ordering = ['created_date']

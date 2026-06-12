from django.db import models

# Create your models here.

class RealChallan(models.Model):
    no = models.CharField(max_lenght=60)
    date = models.CharField(max_lenght=50)
    status = models.CharField(max_lenght=50)
    payment = models.CharField(max_lenght=50)
    sent_court = models.CharField(max_lenght=50)
    remark = models.CharField(max_lenght=150)
    place = models.CharField(max_lenght=50)
    violator_name = models.CharField(max_lenght=50)
    department = models.CharField(max_lenght=50)
    state_code = models.CharField(max_lenght=50)
    owner_name = models.CharField(max_lenght=50)
    user_id = models.CharField(max_lenght=50)
    time = models.DateTimeField()

    class Meta:
        db_table = 'aaaad_real_challan'
        managed = True

class Map(models.Model):
    lat = models.CharField(max_length=50)
    lon = models.CharField(max_length=50)
    
    intensity = models.IntegerField()
    time=model.DateTimeField()
    status = models.CharField(max_length=50, default="approved")

    class Meta:
        db_table = 'aaaad_map'
        managed = True


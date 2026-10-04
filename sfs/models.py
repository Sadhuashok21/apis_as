from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager

class AllUsers(AbstractBaseUser):
    username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=50, unique=True)
    profile = models.CharField(max_length=500, default="profile.webp")
    user_type = models.CharField(max_length=5, default="user")
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    type = models.CharField(max_length=10)
    user_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, default="approved")
    ip = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    objects = UserManager()

    class Meta:
        managed = True
        db_table = 'all_users'



class BpCat(models.Model):
    bp_category = models.CharField(max_length=20)
    bp_name = models.CharField(max_length=35)
    bp_img = models.CharField(max_length=40)
    bp_para = models.TextField()
    category_id = models.CharField(max_length=25, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field = "user_id",
        related_name = "bp_cat_user",
    )
    status = models.CharField(max_length=11)
    ip = models.CharField(max_length=50)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_bp_cat'



class BP(models.Model):
    name = models.CharField(max_length=50)
    image = models.CharField(max_length=50)
    views = models.IntegerField(default=0)
    downloads = models.IntegerField(default=0)
    share = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    fviews = models.IntegerField(default=0)
    flikes = models.IntegerField(default=0)
    fdownloads = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    fshare = models.IntegerField(default=0)
    zipfiles = models.CharField(max_length=50)
    sfs_link = models.CharField(max_length=200)
    type = models.CharField(max_length=20)
    bp_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    ip = models.CharField(max_length=50)
    feature = models.BooleanField(default=0)
    description = models.TextField()
    time = models.DateTimeField()
    user = models.ForeignKey(
        AllUsers, 
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="bp_user",
    )

    class Meta:
        managed = True
        db_table = 'sfs_bp'


class BPCategories(models.Model):
    category = models.ForeignKey(
        BpCat,
        db_column = "category_id",
        to_field = "category_id",
        on_delete = models.CASCADE,
        related_name = "bp_categories",
    )
    bp = models.ForeignKey(
        BP,
        db_column = "bp_id",
        to_field = "bp_id",
        on_delete = models.CASCADE,
        related_name = "bp_category_bp",
    )
    status = models.CharField(max_length=11)
    ip = models.CharField(max_length=50)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_bp_categories'



class Favorites(models.Model):
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="bp_favorites_user",

    )
    bp = models.ForeignKey(
        BP,
        db_column = "bp_id",
        on_delete = models.CASCADE,
        to_field='bp_id',
        related_name="bp_favorites_bp",
    )
    
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_favorites'

class BPImages(models.Model):
    image = models.CharField(max_length=70)
    bp = models.ForeignKey(
        BP,
        db_column = "bp_id",
        on_delete = models.CASCADE,
        to_field='bp_id',
        related_name="bp_user_image",
    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_images'




class BpDlv(models.Model):
    ip = models.CharField(max_length=50)
    bp_pla_id = models.CharField(max_length=35)
    download_type = models.CharField(max_length=10)
    user_id = models.CharField(max_length=50)
    type = models.CharField(max_length=10)
    dlv_id = models.CharField(max_length=50, unique=True)
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    version = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_bp_dlv'


class Comments(models.Model):
    ip = models.CharField(max_length=50)
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field = "user_id",
        related_name = "comments_user",
    )
    bp = models.ForeignKey(
        BP,
        db_column = "bp_id",
        on_delete = models.CASCADE,
        to_field = "bp_id",
        related_name = "comments_bp",
    )
    comment = models.TextField()
    status = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_comments'





# ==============================================================================
# UTILITY & SYSTEM LOGGING MODELS (from shared_lib.utils)
# ==============================================================================





class TotalActivity(models.Model):
    ip = models.CharField(max_length=50)
    user = models.ForeignKey(
            AllUsers,
            null=True,
            blank=True,
            to_field="user_id",
            db_column="user_id",
            related_name="activity_user",
            on_delete=models.CASCADE,
        )
    activity_id = models.CharField(max_length=50)
    total_id = models.CharField(max_length=50)
    platform = models.CharField(max_length=10, default="app")
    platform_name = models.CharField(max_length=50, default="sfs_blueprints")
    version = models.CharField(max_length=15)
    time = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'total_activity'


class AllErrors(models.Model):
    error_id = models.CharField(max_length=50)
    error_msg = models.TextField()
    error_code = models.IntegerField(default=200)
    user = models.ForeignKey(
            AllUsers,
            null=True,
            blank=True,
            to_field="user_id",
            db_column="user_id",
            related_name="error_user",
            on_delete=models.CASCADE,
        )
    ip = models.CharField(max_length=50)
    activity = models.TextField()
    platform = models.CharField(max_length=10, default="app")
    platform_name = models.CharField(max_length=50, default="sfs_blueprints")
    version = models.CharField(max_length=15)
    status = models.CharField(max_length=20, default='active')
    time = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'allerrors'



class DeviceFCM(models.Model):
    device = models.TextField()
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    device_id = models.CharField(max_length=50)
    user = models.ForeignKey(
        AllUsers,
        null=True,
        blank=True,
        to_field="user_id",
        db_column="user_id",
        related_name="device_user",
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=20,  default='active')
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'devices_fcm'



# ==============================================================================
# TRANSPORT HUB TRAIN MODELS (from shared_lib.train_core)
# ==============================================================================



class Trains(models.Model):
    train_id = models.CharField(max_length=100, unique=True)
    train_number = models.CharField(max_length=20, unique=True)
    train_name = models.CharField(max_length=255)
    source_station = models.CharField(max_length=100)
    departure_time = models.TimeField()
    destination_station = models.CharField(max_length=100)
    arrival_time = models.TimeField()
    day = models.IntegerField(default=1)
    frequency = models.CharField(max_length=50, default='Daily')
    own = models.CharField(max_length=100)


    def __str__(self):
        return f"{self.train_name} ({self.train_id})"

    class Meta:
        db_table = 'trains'
        managed = True


class TrainSchedule(models.Model):
    DAYS = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
        ('ALL', 'All Days'),
    ]
    train = models.ForeignKey(
        Trains,
        on_delete=models.CASCADE,
        related_name='schedules',
        db_column='train_id',
        to_field='train_id',
    )
    schedule = models.CharField(max_length=3, choices=DAYS)
    schedule_id = models.CharField(max_length=100, unique=True)
 
    def __str__(self):
        return f"{self.train.train_name} - {self.station} ({self.day_of_week})"

    class Meta:
        db_table = 'train_schedules'
        managed = True

class days(models.Model):
    train = models.ForeignKey(
            Trains,
            on_delete=models.CASCADE,
            related_name='days'
        )
    day_of_week = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.train.train_name} - {self.schedule}"

    class Meta:
        db_table = 'train_days'
        managed = True

class Stations(models.Model):
    station_id = models.CharField(max_length=50, unique=True)
    station_name = models.CharField(max_length=255)
    station_code = models.CharField(max_length=10, unique=True)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zone = models.CharField(max_length=100)
    division = models.CharField(max_length=100)
    station_category = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.station_name} ({self.station_code})"

    class Meta:
        db_table = 'stations'
        managed = True
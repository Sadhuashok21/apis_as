from django.db import models


class AllUsers(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    email = models.CharField(max_length=50)
    password = models.CharField(max_length=35)
    user_id = models.CharField(unique=True, max_length=40)
    profile = models.CharField(max_length=2000)
    user_type = models.CharField(max_length=5)
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    type = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    ip = models.CharField(max_length=50)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'all_users'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'



class SfsBp(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    image = models.CharField(max_length=100)
    views = models.IntegerField()
    downloads = models.IntegerField()
    share = models.IntegerField()
    likes = models.IntegerField()
    fviews = models.IntegerField()
    flikes = models.IntegerField()
    fdownloads = models.IntegerField()
    comments = models.IntegerField()
    fshare = models.IntegerField()
    zipfiles = models.CharField(max_length=250)
    sfs_link = models.CharField(max_length=150)
    category = models.CharField(max_length=30)
    preview1 = models.CharField(max_length=40)
    preview2 = models.CharField(max_length=40)
    preview3 = models.CharField(max_length=40)
    type = models.CharField(max_length=20)
    bp_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=12)
    ip = models.CharField(max_length=50)
    feature = models.BooleanField(default=0)
    time = models.DateTimeField()
    user = models.ForeignKey(
        AllUsers, 
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="bp_user",
    )

    class Meta:
        managed = False
        db_table = 'sfs_bp'



class BPImages(models.Model):
    image = models.CharField(max_length=50)
    bp = models.ForeignKey(
        SfsBp,
        on_delete = models.CASCADE,
        to_field='bp_id',
        related_name="bp_user",
    )
    status = models.CharField(max_length=12)
    time = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'sfs_images'


class SfsBpCat(models.Model):
    id = models.BigAutoField(primary_key=True)
    bp_category = models.CharField(max_length=20)
    bp_name = models.CharField(max_length=35)
    bp_img = models.CharField(max_length=30)
    bp_para = models.TextField()
    category_id = models.CharField(max_length=25)
    status = models.CharField(max_length=11)
    ip = models.CharField(max_length=50)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'sfs_bp_cat'


class SfsBpDlv(models.Model):
    id = models.BigAutoField(primary_key=True)
    ip = models.CharField(max_length=50)
    bp_pla_id = models.CharField(max_length=35)
    download_type = models.CharField(max_length=10)
    user_id = models.CharField(max_length=40)
    type = models.CharField(max_length=10)
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    version = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'sfs_bp_dlv'


class SfsComments(models.Model):
    id = models.BigAutoField(primary_key=True)
    ip = models.CharField(max_length=50)
    user_id = models.CharField(max_length=40)
    blueprint_id = models.CharField(max_length=40)
    comment = models.TextField()
    status = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'sfs_comments'




class TotalActivity(models.Model):
    id = models.BigAutoField(primary_key=True)
    ip = models.CharField(max_length=50)
    user_id = models.CharField(max_length=40)
    activity_id = models.CharField(max_length=500)
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=50)
    version = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'total_activity'


class Allerrors(models.Model):
    id = models.BigAutoField(primary_key=True)
    error_id = models.CharField(max_length=300)
    error_msg = models.CharField(max_length=250)
    user_id = models.CharField(max_length=40)
    ip = models.CharField(max_length=50)
    platform = models.CharField(max_length=10)
    platform_name = models.CharField(max_length=20)
    version = models.CharField(max_length=15)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'allerrors'



from django.db import models


class Stations(models.Model):
    station_name = models.CharField(max_length=100)
    station_code = models.CharField(max_length=10, unique=True)
   
    def __str__(self):
        return f"{self.station_name} ({self.station_code})"

    class Meta:
        managed = True
        db_table = "th_stations"





class Trains(models.Model):
    train_no = models.PositiveIntegerField(unique=True)
    train_name = models.CharField(max_length=100)

    from_station = models.ForeignKey(
        Stations,
        to_field="station_code",
        on_delete=models.PROTECT,
        db_column="from_station_id",
        related_name="departing_trains",
    )

    to_station = models.ForeignKey(
        Stations,
        to_field="station_code",
        on_delete=models.PROTECT,
        db_column="to_station_id",
        related_name="arriving_trains",
    )

    train_type = models.CharField(max_length=50, blank=True, null=True)
    total_distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.train_no} - {self.train_name}"

    class Meta:
        managed = True
        db_table = "th_trains"

class TrainOperatingDays(models.Model):

    class WeekDays(models.TextChoices):
        MONDAY = "MON", "Monday"
        TUESDAY = "TUE", "Tuesday"
        WEDNESDAY = "WED", "Wednesday"
        THURSDAY = "THU", "Thursday"
        FRIDAY = "FRI", "Friday"
        SATURDAY = "SAT", "Saturday"
        SUNDAY = "SUN", "Sunday"

    train = models.ForeignKey(
        Trains,
        on_delete=models.CASCADE,
        related_name="operating_days",
    )

    day = models.CharField(
        max_length=3,
        choices=WeekDays.choices,
    )

    def __str__(self):
        return f"{self.train.train_no} - {self.day}"

    class Meta:
        managed = True
        db_table = "th_train_operating_days"
        constraints = [
            models.UniqueConstraint(
                fields=["train", "day"],
                name="unique_train_operating_day",
            )
        ]


class Accomdation(models.Model):
    class_code = models.CharField(max_length=10, unique=True)
    class_name = models.CharField(max_length=100)

    is_ac = models.BooleanField(default=False)
    is_seating = models.BooleanField(default=False)

    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.class_code} - {self.class_name}"

    class Meta:
        managed = True
        db_table = "th_accomdation"


class TrainAccomdation(models.Model):
    train = models.ForeignKey(
        Trains,
        on_delete=models.CASCADE,
        related_name="accommodations",
    )

    accommodation = models.ForeignKey(
        Accomdation,
        on_delete=models.PROTECT,
        related_name="trains",
    )

    def __str__(self):
        return f"{self.train.train_no} - {self.accommodation.class_code}"

    class Meta:
        managed = True
        db_table = "th_train_accomdation"
        constraints = [
            models.UniqueConstraint(
                fields=["train", "accommodation"],
                name="unique_train_accommodation",
            )
        ]




class TrainStops(models.Model):
    train = models.ForeignKey(
        Trains,
        on_delete=models.CASCADE,
        related_name="stops",
        db_column="train_id",
    )

    from_station = models.ForeignKey(
        Stations,
        on_delete=models.PROTECT,
        related_name="train_stops_from",
        db_column="from_station_id",
    )


    to_station = models.ForeignKey(
        Stations,
        on_delete=models.PROTECT,
        related_name="train_stops_to",
        db_column="to_station_id",
    )

    is_stop = models.BooleanField(default=False)

    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)

    distance_from_source_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.train.train_no} - {self.station.station_code}"

    class Meta:
        managed = True
        db_table = "th_train_stops"
        

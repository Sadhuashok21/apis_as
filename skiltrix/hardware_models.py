import uuid
from django.db import models
from sfs.models import AllUsers


class HardwareBoard(models.Model):
    FAMILY_CHOICES = (
        ("arduino", "Arduino AVR / ARM"),
        ("esp32", "Espressif ESP32"),
        ("stm32", "STM32 ARM Cortex"),
        ("rp2040", "Raspberry Pi RP2040"),
    )

    board_id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=150)
    family = models.CharField(max_length=30, choices=FAMILY_CHOICES, default="esp32")
    mcu = models.CharField(max_length=100, help_text="e.g. ESP32-WROOM-32, ATmega328P, ESP32-S3")
    clock_speed_mhz = models.PositiveIntegerField(default=240)
    flash_size_mb = models.FloatField(default=4.0)
    ram_kb = models.FloatField(default=520.0)
    operating_voltage = models.FloatField(default=3.3)
    gpio_count = models.PositiveIntegerField(default=34)
    has_wifi = models.BooleanField(default=True)
    has_ble = models.BooleanField(default=True)
    platformio_env = models.CharField(max_length=100, default="esp32dev")
    arduino_fqbn = models.CharField(max_length=150, default="esp32:esp32:esp32")
    pinout_data = models.JSONField(default=dict, blank=True, help_text="GPIO pinout mappings and peripheral capabilities")
    schematic_symbol = models.CharField(max_length=100, blank=True, default="")
    default_template_code = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_hardware_boards"
        ordering = ["family", "name"]

    def __str__(self):
        return f"{self.name} ({self.mcu})"


class HardwareProject(models.Model):
    PROJECT_TYPES = (
        ("arduino_sketch", "Arduino C/C++ Sketch"),
        ("esp_idf", "ESP-IDF Framework Project"),
        ("platformio", "PlatformIO Embedded Project"),
        ("bare_metal", "Bare Metal C/C++"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("configured", "Configured"),
        ("verified", "Verified"),
        ("error", "Build Error"),
    )

    project_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        related_name="hardware_projects",
        db_column="user_id",
        to_field="user_id",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True, default="")
    project_type = models.CharField(max_length=40, choices=PROJECT_TYPES, default="platformio")
    target_board = models.ForeignKey(
        HardwareBoard,
        on_delete=models.PROTECT,
        related_name="projects",
        null=True,
        blank=True,
    )
    board_variant = models.CharField(max_length=100, blank=True, default="ESP32-WROOM-32E")
    baud_rate = models.PositiveIntegerField(default=115200)
    cpu_freq_mhz = models.PositiveIntegerField(default=240)
    flash_mode = models.CharField(max_length=20, default="qio")
    partitions_config = models.CharField(max_length=100, default="default.csv")
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    build_settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_hardware_projects"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.project_id}) - {self.target_board_id or 'No Board'}"


class HardwareSourceFile(models.Model):
    file_id = models.CharField(max_length=64, primary_key=True)
    project = models.ForeignKey(
        HardwareProject,
        on_delete=models.CASCADE,
        related_name="source_files",
        db_column="project_id",
    )
    path = models.CharField(max_length=300, help_text="Relative path, e.g. src/main.cpp or include/config.h")
    name = models.CharField(max_length=120)
    content = models.TextField(blank=True, default="")
    is_main_entry = models.BooleanField(default=False)
    size_bytes = models.PositiveIntegerField(default=0)
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_hardware_source_files"
        unique_together = ("project", "path")
        ordering = ["path"]

    def __str__(self):
        return f"{self.project_id}: {self.path}"

    def save(self, *args, **kwargs):
        if self.content:
            self.size_bytes = len(self.content.encode("utf-8"))
        super().save(*args, **kwargs)


class PcbProject(models.Model):
    STATUS_CHOICES = (
        ("draft", "Design in Progress"),
        ("erc_passed", "ERC Passed"),
        ("drc_passed", "DRC Passed"),
        ("ready_for_fab", "Manufacturing Ready"),
        ("violations", "Design Rule Violations"),
    )

    pcb_id = models.CharField(max_length=64, primary_key=True)
    hardware_project = models.OneToOneField(
        HardwareProject,
        on_delete=models.CASCADE,
        related_name="pcb_project",
    )
    title = models.CharField(max_length=200)
    layer_count = models.PositiveSmallIntegerField(default=2, help_text="Number of copper layers (2, 4, 6)")
    board_width_mm = models.FloatField(default=50.0)
    board_height_mm = models.FloatField(default=40.0)
    copper_weight_oz = models.FloatField(default=1.0)
    min_trace_width_mil = models.FloatField(default=6.0)
    min_clearance_mil = models.FloatField(default=6.0)
    solder_mask_color = models.CharField(max_length=20, default="green")
    silkscreen_color = models.CharField(max_length=20, default="white")
    surface_finish = models.CharField(max_length=30, default="HASL_lead_free")
    schematic_data = models.JSONField(default=dict, blank=True, help_text="KiCad-compatible schematic symbol and net definitions")
    layout_data = models.JSONField(default=dict, blank=True, help_text="KiCad-compatible footprint positions, tracks, and vias")
    erc_log = models.JSONField(default=list, blank=True)
    drc_log = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_hardware_pcb_projects"

    def __str__(self):
        return f"PCB for {self.hardware_project.title} ({self.layer_count}-Layer)"


class ComponentItem(models.Model):
    component_id = models.CharField(max_length=64, primary_key=True)
    pcb_project = models.ForeignKey(
        PcbProject,
        on_delete=models.CASCADE,
        related_name="components",
    )
    reference = models.CharField(max_length=20, help_text="Designator, e.g. R1, C1, U1, ESP32_MOD1")
    value = models.CharField(max_length=100, help_text="e.g. 10k, 100nF, ESP32-WROOM-32E, AMS1117-3.3")
    footprint = models.CharField(max_length=150, help_text="e.g. Resistor_SMD:R_0805_2012Metric")
    symbol = models.CharField(max_length=100, default="Device:R")
    manufacturer = models.CharField(max_length=150, blank=True, default="")
    mpn = models.CharField(max_length=150, blank=True, default="", help_text="Manufacturer Part Number")
    datasheet_url = models.URLField(max_length=500, blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)
    unit_cost_inr = models.FloatField(default=0.0)
    is_surface_mount = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = "st_hardware_components"
        unique_together = ("pcb_project", "reference")
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference}: {self.value} ({self.footprint})"


class HardwareBuildJob(models.Model):
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("building", "Building"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("unsupported", "Compiler Toolchain Unavailable"),
    )

    job_id = models.CharField(max_length=64, primary_key=True)
    project = models.ForeignKey(
        HardwareProject,
        on_delete=models.CASCADE,
        related_name="build_jobs",
    )
    toolchain = models.CharField(max_length=40, default="platformio")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    stdout_log = models.TextField(blank=True, default="")
    stderr_log = models.TextField(blank=True, default="")
    flash_used_bytes = models.PositiveIntegerField(default=0)
    ram_used_bytes = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(default=0.0)
    binary_artifact_url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_hardware_build_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.job_id} ({self.project.title}): {self.status}"


class ConnectedDevice(models.Model):
    device_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        related_name="hardware_devices",
        db_column="user_id",
        to_field="user_id",
    )
    name = models.CharField(max_length=120)
    board = models.ForeignKey(
        HardwareBoard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    serial_port = models.CharField(max_length=100, blank=True, default="COM3")
    baud_rate = models.PositiveIntegerField(default=115200)
    firmware_version = models.CharField(max_length=50, blank=True, default="1.0.0")
    is_online = models.BooleanField(default=False)
    last_telemetry = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_hardware_connected_devices"
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"{self.name} ({self.device_id}) - {self.serial_port}"


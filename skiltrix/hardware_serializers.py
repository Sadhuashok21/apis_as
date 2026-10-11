from rest_framework import serializers
from .hardware_models import (
    HardwareBoard,
    HardwareProject,
    HardwareSourceFile,
    PcbProject,
    ComponentItem,
    HardwareBuildJob,
    ConnectedDevice,
)


class HardwareBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareBoard
        fields = "__all__"


class HardwareSourceFileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareSourceFile
        fields = ["file_id", "path", "name", "is_main_entry", "size_bytes", "revision", "updated_at"]


class HardwareSourceFileDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareSourceFile
        fields = ["file_id", "project", "path", "name", "content", "is_main_entry", "size_bytes", "revision", "updated_at"]
        read_only_fields = ["size_bytes", "revision", "updated_at"]


class ComponentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentItem
        fields = "__all__"


class PcbProjectSerializer(serializers.ModelSerializer):
    components = ComponentItemSerializer(many=True, read_only=True)
    component_count = serializers.SerializerMethodField()

    class Meta:
        model = PcbProject
        fields = [
            "pcb_id", "hardware_project", "title", "layer_count", "board_width_mm", "board_height_mm",
            "copper_weight_oz", "min_trace_width_mil", "min_clearance_mil", "solder_mask_color",
            "silkscreen_color", "surface_finish", "schematic_data", "layout_data", "erc_log", "drc_log",
            "status", "components", "component_count", "updated_at"
        ]

    def get_component_count(self, obj):
        return obj.components.count()


class HardwareBuildJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareBuildJob
        fields = "__all__"
        read_only_fields = ["created_at"]


class ConnectedDeviceSerializer(serializers.ModelSerializer):
    board_name = serializers.ReadOnlyField(source="board.name")

    class Meta:
        model = ConnectedDevice
        fields = [
            "device_id", "user", "name", "board", "board_name", "serial_port", "baud_rate",
            "firmware_version", "is_online", "last_telemetry", "last_seen_at", "created_at"
        ]


class HardwareProjectListSerializer(serializers.ModelSerializer):
    target_board_name = serializers.ReadOnlyField(source="target_board.name")
    target_board_mcu = serializers.ReadOnlyField(source="target_board.mcu")
    target_board_family = serializers.ReadOnlyField(source="target_board.family")
    target_board_detail = HardwareBoardSerializer(source="target_board", read_only=True)
    file_count = serializers.SerializerMethodField()
    has_pcb = serializers.SerializerMethodField()

    class Meta:
        model = HardwareProject
        fields = [
            "project_id", "user", "title", "slug", "description", "project_type", "target_board",
            "target_board_name", "target_board_mcu", "target_board_family", "target_board_detail",
            "board_variant", "baud_rate", "cpu_freq_mhz", "flash_mode", "status", "file_count",
            "has_pcb", "created_at", "updated_at"
        ]

    def get_file_count(self, obj):
        return obj.source_files.count()

    def get_has_pcb(self, obj):
        return hasattr(obj, "pcb_project")


class HardwareProjectDetailSerializer(serializers.ModelSerializer):
    target_board_detail = HardwareBoardSerializer(source="target_board", read_only=True)
    source_files = HardwareSourceFileDetailSerializer(many=True, read_only=True)
    pcb_project = PcbProjectSerializer(read_only=True)
    recent_build = serializers.SerializerMethodField()

    class Meta:
        model = HardwareProject
        fields = [
            "project_id", "user", "title", "slug", "description", "project_type", "target_board",
            "target_board_detail", "board_variant", "baud_rate", "cpu_freq_mhz", "flash_mode",
            "partitions_config", "status", "build_settings", "source_files", "pcb_project",
            "recent_build", "created_at", "updated_at"
        ]

    def get_recent_build(self, obj):
        last_job = obj.build_jobs.first()
        if last_job:
            return HardwareBuildJobSerializer(last_job).data
        return None



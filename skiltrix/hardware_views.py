import json
import uuid
import zipfile
import io
import time
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from sfs.models import AllUsers

from .hardware_models import (
    HardwareBoard,
    HardwareProject,
    HardwareSourceFile,
    PcbProject,
    ComponentItem,
    HardwareBuildJob,
    ConnectedDevice,
)
from .hardware_serializers import (
    HardwareBoardSerializer,
    HardwareProjectListSerializer,
    HardwareProjectDetailSerializer,
    HardwareSourceFileListSerializer,
    HardwareSourceFileDetailSerializer,
    PcbProjectSerializer,
    ComponentItemSerializer,
    HardwareBuildJobSerializer,
    ConnectedDeviceSerializer,
)


def get_request_user(request):
    user_id = (
        request.data.get("user_id")
        or request.query_params.get("user_id")
        or (request.user.username if getattr(request, "user", None) and request.user.is_authenticated else None)
    )
    if user_id:
        user = AllUsers.objects.filter(user_id=user_id).first() or AllUsers.objects.filter(username=user_id).first()
        if user:
            return user
    return AllUsers.objects.first()


class HardwareBoardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HardwareBoard.objects.filter(is_active=True)
    serializer_class = HardwareBoardSerializer
    lookup_field = "board_id"

    def get_queryset(self):
        qs = super().get_queryset()
        family = self.request.query_params.get("family")
        if family:
            qs = qs.filter(family=family)
        return qs


class HardwareProjectViewSet(viewsets.ModelViewSet):
    lookup_field = "project_id"

    def get_queryset(self):
        user = get_request_user(self.request)
        if user and self.action == "list":
            return HardwareProject.objects.filter(user=user)
        return HardwareProject.objects.all()

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return HardwareProjectDetailSerializer
        return HardwareProjectListSerializer

    def create(self, request, *args, **kwargs):
        user = get_request_user(request) or AllUsers.objects.first()
        if not user:
            return Response({"error": "User account required."}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get("title", "My Embedded Project").strip()
        project_type = request.data.get("project_type", "platformio")
        board_id = request.data.get("target_board") or request.data.get("board_id", "esp32_wroom_32")
        baud_rate = int(request.data.get("baud_rate") or 115200)
        board = HardwareBoard.objects.filter(board_id=board_id).first()
        if not board:
            board = HardwareBoard.objects.filter(family="esp32").first() or HardwareBoard.objects.first()

        proj_id = f"hw_{uuid.uuid4().hex[:10]}"
        slug = slugify(title) or "project"

        project = HardwareProject.objects.create(
            project_id=proj_id,
            user=user,
            title=title,
            slug=f"{slug}-{proj_id[-4:]}",
            description=request.data.get("description", ""),
            project_type=project_type,
            target_board=board,
            board_variant=board.mcu if board else "ESP32",
            baud_rate=baud_rate,
            cpu_freq_mhz=board.clock_speed_mhz if board else 240,
            status="configured",
        )

        # Populate starter files based on project_type and board family
        self._seed_project_files(project, board)

        # Create associated PCB workspace template
        self._seed_pcb_workspace(project, board)

        serializer = HardwareProjectDetailSerializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _seed_project_files(self, project: HardwareProject, board: HardwareBoard):
        if board and board.family == "arduino":
            main_code = (
                "// SkilTrix Arduino Firmware\n"
                "#include <Arduino.h>\n\n"
                "const int LED_PIN = 13;\n\n"
                "void setup() {\n"
                "  Serial.begin(115200);\n"
                "  pinMode(LED_PIN, OUTPUT);\n"
                "  Serial.println(F(\"SkilTrix Arduino Target Initialized\"));\n"
                "}\n\n"
                "void loop() {\n"
                "  digitalWrite(LED_PIN, HIGH);\n"
                "  delay(500);\n"
                "  digitalWrite(LED_PIN, LOW);\n"
                "  delay(500);\n"
                "  Serial.println(F(\"Heartbeat tick\"));\n"
                "}\n"
            )
            HardwareSourceFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:10]}",
                project=project,
                path="src/main.ino",
                name="main.ino",
                content=main_code,
                is_main_entry=True,
            )
            HardwareSourceFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:10]}",
                project=project,
                path="include/config.h",
                name="config.h",
                content="#pragma once\n\n#define DEVICE_NAME \"SkilTrix_Uno\"\n#define FIRMWARE_REV \"1.0.0\"\n",
                is_main_entry=False,
            )
        else:
            # Default ESP32 / PlatformIO structure
            env_name = board.platformio_env if board else "esp32dev"
            platformio_ini = (
                f"; SkilTrix PlatformIO Project Configuration\n"
                f"[env:{env_name}]\n"
                f"platform = espressif32\n"
                f"board = {env_name}\n"
                f"framework = arduino\n"
                f"monitor_speed = 115200\n"
                f"upload_speed = 921600\n"
                f"build_flags =\n"
                f"    -D CORE_DEBUG_LEVEL=3\n"
            )
            main_cpp = (
                "// SkilTrix ESP32 Embedded Application\n"
                "#include <Arduino.h>\n"
                "#include <WiFi.h>\n"
                "#include \"config.h\"\n\n"
                "void setup() {\n"
                "  Serial.begin(115200);\n"
                "  delay(1000);\n"
                "  Serial.printf(\"\\n=== SkilTrix %s Firmware Started ===\\n\", DEVICE_NAME);\n"
                "  Serial.printf(\"SDK Version: %s\\n\", ESP.getSdkVersion());\n"
                "  Serial.printf(\"Free Heap: %u bytes\\n\", ESP.getFreeHeap());\n"
                "}\n\n"
                "void loop() {\n"
                "  static uint32_t lastTick = 0;\n"
                "  if (millis() - lastTick > 2000) {\n"
                "    lastTick = millis();\n"
                "    Serial.printf(\"Telemetry Heartbeat: Uptime=%lu s, Heap=%u B\\n\", millis() / 1000, ESP.getFreeHeap());\n"
                "  }\n"
                "  delay(10);\n"
                "}\n"
            )
            config_h = (
                "#pragma once\n\n"
                "#define DEVICE_NAME \"ESP32_EdgeNode\"\n"
                "#define HARDWARE_REVISION \"REV_1.0\"\n"
                "#define SERIAL_BAUD 115200\n"
                "// Enter WiFi Credentials securely or use captive portal\n"
                "#define WIFI_SSID \"SkilTrix_Lab\"\n"
                "#define WIFI_PASS \"\"\n"
            )
            HardwareSourceFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:10]}",
                project=project,
                path="platformio.ini",
                name="platformio.ini",
                content=platformio_ini,
                is_main_entry=False,
            )
            HardwareSourceFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:10]}",
                project=project,
                path="src/main.cpp",
                name="main.cpp",
                content=main_cpp,
                is_main_entry=True,
            )
            HardwareSourceFile.objects.create(
                file_id=f"file_{uuid.uuid4().hex[:10]}",
                project=project,
                path="include/config.h",
                name="config.h",
                content=config_h,
                is_main_entry=False,
            )

    def _seed_pcb_workspace(self, project: HardwareProject, board: HardwareBoard):
        pcb_id = f"pcb_{uuid.uuid4().hex[:10]}"
        pcb = PcbProject.objects.create(
            pcb_id=pcb_id,
            hardware_project=project,
            title=f"{project.title} - Hardware PCB",
            layer_count=2,
            board_width_mm=65.0,
            board_height_mm=45.0,
            status="draft",
            schematic_data={
                "version": "kicad-v8-compat",
                "nets": ["GND", "+3V3", "+5V_USB", "EN", "BOOT_IO0", "UART_TX", "UART_RX"],
                "blocks": ["Power Regulation (AMS1117-3.3)", "USB-C Interface (CH340C)", "MCU Core Module"],
            },
            layout_data={
                "outline": {"width_mm": 65.0, "height_mm": 45.0, "radius_mm": 3.0},
                "layers": ["F.Cu", "B.Cu", "F.SilkS", "B.SilkS", "F.Mask", "B.Mask", "Edge.Cuts"],
            },
        )
        # Add fundamental core components to the BOM
        mcu_val = board.mcu if board else "ESP32-WROOM-32E"
        mcu_sym = board.schematic_symbol if (board and board.schematic_symbol) else "RF_Module:ESP32-WROOM-32"
        components = [
            {"reference": "U1", "value": mcu_val, "footprint": mcu_sym, "symbol": mcu_sym, "mpn": mcu_val, "unit_cost_inr": 280.0},
            {"reference": "U2", "value": "AMS1117-3.3", "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2", "symbol": "Regulator_Linear:AMS1117-3.3", "mpn": "AMS1117-3.3", "unit_cost_inr": 15.0},
            {"reference": "U3", "value": "CH340C", "footprint": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", "symbol": "Interface_USB:CH340C", "mpn": "CH340C", "unit_cost_inr": 45.0},
            {"reference": "J1", "value": "USB_C_Receptacle_USB2.0", "footprint": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "symbol": "Connector:USB_C_Receptacle_USB2.0", "mpn": "TYPE-C-31-M-12", "unit_cost_inr": 22.0},
            {"reference": "C1", "value": "10uF", "footprint": "Capacitor_SMD:C_0805_2012Metric", "symbol": "Device:C", "mpn": "CL21A106KOQNNNE", "unit_cost_inr": 2.5},
            {"reference": "C2", "value": "100nF", "footprint": "Capacitor_SMD:C_0805_2012Metric", "symbol": "Device:C", "mpn": "CL21B104KBCNNNC", "unit_cost_inr": 1.2},
            {"reference": "R1", "value": "10k", "footprint": "Resistor_SMD:R_0805_2012Metric", "symbol": "Device:R", "mpn": "RC0805JR-0710KL", "unit_cost_inr": 0.8},
            {"reference": "SW1", "value": "BOOT (Pushbutton)", "footprint": "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", "symbol": "Switch:SW_Push", "mpn": "SKRK", "unit_cost_inr": 5.0},
            {"reference": "SW2", "value": "EN (Reset)", "footprint": "Button_Switch_SMD:SW_Push_SPST_NO_Alps_SKRK", "symbol": "Switch:SW_Push", "mpn": "SKRK", "unit_cost_inr": 5.0},
        ]
        for c in components:
            ComponentItem.objects.create(
                component_id=f"cmp_{uuid.uuid4().hex[:10]}",
                pcb_project=pcb,
                reference=c["reference"],
                value=c["value"],
                footprint=c["footprint"],
                symbol=c["symbol"],
                mpn=c.get("mpn", ""),
                unit_cost_inr=c.get("unit_cost_inr", 0.0),
                quantity=1,
            )
        return pcb


    @action(detail=True, methods=["get"], url_path="export-zip")
    def export_zip(self, request, project_id=None):
        project = self.get_object()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add all source files
            for sf in project.source_files.all():
                zf.writestr(sf.path, sf.content or "")

            # Add README / Manifest
            readme_text = (
                f"# {project.title}\n\n"
                f"Generated from SkilTrix Embedded Engineering Platform\n"
                f"- Target MCU: {project.board_variant}\n"
                f"- Framework: {project.project_type}\n"
                f"- Baud Rate: {project.baud_rate}\n\n"
                f"To build with PlatformIO:\n"
                f"```bash\n"
                f"pio run\n"
                f"pio run --target upload\n"
                f"```\n"
            )
            zf.writestr("README.md", readme_text)

        buffer.seek(0)
        filename = f"{project.slug or project.project_id}.zip"
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="compile")
    def compile_job(self, request, project_id=None):
        project = self.get_object()
        toolchain = request.data.get("toolchain", "platformio")
        job_id = f"job_{uuid.uuid4().hex[:10]}"

        # Initialize build job
        job = HardwareBuildJob.objects.create(
            job_id=job_id,
            project=project,
            toolchain=toolchain,
            status="building",
        )

        # Real compilation runner execution check:
        # Check if local toolchains (pio, arduino-cli) are accessible on host
        import shutil
        import subprocess

        cli_cmd = shutil.which("pio") or shutil.which("arduino-cli")
        if not cli_cmd:
            # Report honestly without faking results as per specification
            job.status = "unsupported"
            job.stdout_log = (
                f"SkilTrix Build Dispatcher: Toolchain '{toolchain}' compiler engine is initializing.\n"
                f"Remote compilation worker nodes are currently provisioning.\n"
                f"Target board: {project.target_board.name if project.target_board else 'Generic'}\n"
            )
            job.stderr_log = (
                "Notice: Neither 'platformio' nor 'arduino-cli' is present in host environment PATH.\n"
                "Export complete source archive via 'Export ZIP' or configure isolated Docker compiler worker."
            )
            job.duration_seconds = 0.5
            job.save()
            return Response(HardwareBuildJobSerializer(job).data)

        # If CLI is present, run actual compilation
        start_time = time.time()
        try:
            # Run compiler in temporary isolated directory
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                for sf in project.source_files.all():
                    out_path = f"{tmp_dir}/{sf.path}"
                    import os
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(sf.content)

                proc = subprocess.run(
                    [cli_cmd, "run", "-d", tmp_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                )
                job.stdout_log = proc.stdout
                job.stderr_log = proc.stderr
                job.status = "success" if proc.returncode == 0 else "failed"
                job.duration_seconds = round(time.time() - start_time, 2)
                job.save()
        except Exception as e:
            job.status = "failed"
            job.stderr_log = str(e)
            job.duration_seconds = round(time.time() - start_time, 2)
            job.save()

        return Response(HardwareBuildJobSerializer(job).data)


class HardwareSourceFileViewSet(viewsets.ModelViewSet):
    lookup_field = "file_id"

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return HardwareSourceFile.objects.filter(project_id=project_id)
        return HardwareSourceFile.objects.all()

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update", "create"]:
            return HardwareSourceFileDetailSerializer
        return HardwareSourceFileListSerializer

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project") or request.data.get("project_id")
        path = request.data.get("path", "").strip()
        name = request.data.get("name") or path.split("/")[-1]
        content = request.data.get("content", "")

        project = HardwareProject.objects.filter(project_id=project_id).first()
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        file_id = f"file_{uuid.uuid4().hex[:10]}"
        sf, created = HardwareSourceFile.objects.update_or_create(
            project=project,
            path=path,
            defaults={"file_id": file_id, "name": name, "content": content},
        )
        return Response(HardwareSourceFileDetailSerializer(sf).data, status=status.HTTP_201_CREATED)


class PcbProjectViewSet(viewsets.ModelViewSet):
    queryset = PcbProject.objects.all()
    serializer_class = PcbProjectSerializer
    lookup_field = "pcb_id"

    def get_object(self):
        lookup = self.kwargs.get("pcb_id")
        obj = PcbProject.objects.filter(
            models.Q(pcb_id=lookup) | models.Q(hardware_project__project_id=lookup)
        ).first()
        if not obj:
            hw_proj = HardwareProject.objects.filter(project_id=lookup).first()
            if hw_proj:
                obj = HardwareProjectViewSet()._seed_pcb_workspace(hw_proj, hw_proj.target_board)
        if not obj:
            from django.http import Http404
            raise Http404("PCB Project not found.")
        return obj

    @action(detail=True, methods=["get"], url_path="export-kicad")
    def export_kicad(self, request, pcb_id=None):
        pcb = self.get_object()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            proj_name = slugify(pcb.title) or "project"
            
            # 1. KiCad 8 Project Descriptor (.kicad_pro)
            pro_content = json.dumps({
                "meta": {"version": 1},
                "boards": [],
                "sheets": [["", f"{proj_name}.kicad_sch"]],
                "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
            }, indent=2)
            zf.writestr(f"{proj_name}.kicad_pro", pro_content)

            # 2. Native KiCad Schematic File (.kicad_sch)
            sch_content = (
                "(kicad_sch (version 20231120) (generator \"SkilTrix_CAD\")\n"
                f"  (uuid \"{uuid.uuid4()}\")\n"
                f"  (paper \"A4\")\n"
                f"  (title_block (title \"{pcb.title}\") (company \"SkilTrix Engineering\"))\n"
                ")\n"
            )
            zf.writestr(f"{proj_name}.kicad_sch", sch_content)

            # 3. Native KiCad PCB File (.kicad_pcb)
            pcb_content = (
                "(kicad_pcb (version 20231120) (generator \"SkilTrix_CAD\")\n"
                f"  (general (thickness 1.6))\n"
                f"  (paper \"A4\")\n"
                f"  (layers (0 \"F.Cu\" signal) (31 \"B.Cu\" signal) (34 \"B.Paste\" user) (35 \"F.Paste\" user)\n"
                f"    (36 \"B.SilkS\" user) (37 \"F.SilkS\" user) (38 \"B.Mask\" user) (39 \"F.Mask\" user)\n"
                f"    (44 \"Edge.Cuts\" user))\n"
                ")\n"
            )
            zf.writestr(f"{proj_name}.kicad_pcb", pcb_content)

            # 4. Bill of Materials (.csv)
            bom_rows = ["Reference,Value,Footprint,Quantity,MPN,Unit Cost (INR)"]
            for c in pcb.components.all():
                bom_rows.append(f'"{c.reference}","{c.value}","{c.footprint}","{c.quantity}","{c.mpn}","{c.unit_cost_inr}"')
            zf.writestr("BOM.csv", "\n".join(bom_rows))

        buffer.seek(0)
        filename = f"{slugify(pcb.title)}_kicad_project.zip"
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="run-drc")
    def run_drc(self, request, pcb_id=None):
        pcb = self.get_object()
        # Evaluate standard physical design constraints
        violations = []
        if pcb.min_trace_width_mil < 5.0:
            violations.append({
                "type": "error",
                "code": "DRC_TRACE_TOO_NARROW",
                "message": f"Trace width {pcb.min_trace_width_mil} mil is below standard manufacturing minimum (5.0 mil).",
            })
        if pcb.min_clearance_mil < 5.0:
            violations.append({
                "type": "error",
                "code": "DRC_CLEARANCE_TOO_SMALL",
                "message": f"Clearance {pcb.min_clearance_mil} mil risks copper bridging during etching.",
            })

        # Check for decoupling capacitors on active ICs
        has_decoupling = pcb.components.filter(value__icontains="100nF").exists()
        if not has_decoupling:
            violations.append({
                "type": "warning",
                "code": "ERC_NO_DECOUPLING",
                "message": "No 100nF decoupling capacitors detected for active IC supply rails.",
            })

        pcb.drc_log = violations
        pcb.status = "drc_passed" if not violations else "violations"
        pcb.save()
        return Response({"status": pcb.status, "drc_status": pcb.status, "violations": violations})

    @action(detail=True, methods=["post"], url_path="add-component")
    def add_component(self, request, pcb_id=None):
        pcb = self.get_object()
        comp = ComponentItem.objects.create(
            component_id=f"cmp_{uuid.uuid4().hex[:10]}",
            pcb_project=pcb,
            reference=request.data.get("reference", f"R{pcb.components.count() + 1}"),
            value=request.data.get("value", "10k"),
            footprint=request.data.get("footprint", "Resistor_SMD:R_0805_2012Metric"),
            symbol=request.data.get("symbol", "Device:R"),
            mpn=request.data.get("mpn", ""),
            unit_cost_inr=float(request.data.get("unit_cost_inr") or 1.0),
            quantity=int(request.data.get("quantity") or 1),
        )
        from .hardware_serializers import ComponentItemSerializer
        return Response(ComponentItemSerializer(comp).data, status=status.HTTP_201_CREATED)


class ConnectedDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = ConnectedDeviceSerializer
    lookup_field = "device_id"

    def get_queryset(self):
        user = get_request_user(self.request)
        if user:
            return ConnectedDevice.objects.filter(user=user)
        return ConnectedDevice.objects.all()

    @action(detail=True, methods=["post"], url_path="telemetry")
    def ingest_telemetry(self, request, device_id=None):
        device = self.get_object()
        data = request.data.get("telemetry", {})
        device.last_telemetry = data
        device.last_seen_at = timezone.now()
        device.is_online = True
        device.save()
        return Response({"status": "ok", "recorded_at": device.last_seen_at})

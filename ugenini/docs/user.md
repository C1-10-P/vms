vms_project/
│
├── 📁 hardware/                                 # Hardware configuration files
│   ├── 📁 esp32_cam/
│   │   ├── camera_pins.h                        # Camera pin configuration
│   │   ├── config.h                              # WiFi/MQTT configuration
│   │   ├── secrets.h                             # Credentials (not in repo)
│   │   └── wiring_diagram.png                    # Wiring instructions
│   ├── 📁 esp32_c3/
│   │   ├── ble_config.h                          # BLE scanning config
│   │   ├── pins.h                                # GPIO pin mapping
│   │   └── battery_monitor.h                     # Battery monitoring
│   ├── 📁 raspberry_pi/
│   │   ├── 📁 setup/
│   │   │   ├── install.sh                        # One-click install script
│   │   │   ├── docker-compose.yml                # Docker setup
│   │   │   └── requirements.txt                  # Python dependencies
│   │   ├── 📁 config/
│   │   │   ├── mosquitto.conf                    # MQTT broker config
│   │   │   ├── nginx.conf                        # Web server config
│   │   │   ├── supervisor.conf                   # Process manager
│   │   │   └── gunicorn.py                       # WSGI server config
│   │   └── 📁 scripts/
│   │       ├── start_services.sh                 # Start all services
│   │       ├── backup_db.sh                      # Database backup
│   │       └── monitor.sh                        # System monitoring
│   ├── 📁 schematics/
│   │   ├── complete_wiring.pdf                   # Full wiring diagram
│   │   ├── power_supply.pdf                      # Power requirements
│   │   └── network_topology.pdf                  # Network layout
│   └── README_HARDWARE.md                        # Hardware setup guide
│
├── 📁 firmware/                                   # ESP32 Firmware Code
│   ├── 📁 common/
│   │   ├── 📁 include/
│   │   │   ├── config.h
│   │   │   ├── mqtt_client.h
│   │   │   ├── wifi_manager.h
│   │   │   └── utils.h
│   │   └── 📁 src/
│   │       ├── mqtt_client.cpp
│   │       ├── wifi_manager.cpp
│   │       └── utils.cpp
│   ├── 📁 nodes/
│   │   ├── 📁 camera_node/
│   │   │   ├── camera_node.ino
│   │   │   ├── camera_config.h
│   │   │   ├── qr_decoder.cpp
│   │   │   ├── motion_sensor.cpp
│   │   │   └── platformio.ini
│   │   ├── 📁 ble_scanner_node/
│   │   │   ├── ble_scanner.ino
│   │   │   ├── ble_scan.cpp
│   │   │   ├── tag_tracker.cpp
│   │   │   ├── rssi_filter.cpp
│   │   │   └── platformio.ini
│   │   └── 📁 gateway_node/
│   │       ├── gateway.ino
│   │       ├── protocol_converter.cpp
│   │       ├── data_buffer.cpp
│   │       └── platformio.ini
│   └── 📁 libraries/
│       ├── 📁 VMS_QR/
│       └── 📁 VMS_BLE/
│
├── 📁 backend/                                   # Raspberry Pi Backend
│   ├── 📁 config/
│   │   ├── mqtt_broker.conf
│   │   ├── nginx.conf
│   │   ├── supervisors/
│   │   └── logging.conf
│   ├── 📁 database/
│   │   ├── schema.sql
│   │   ├── migrations/
│   │   ├── seed/
│   │   ├── queries/
│   │   └── procedures/
│   ├── 📁 api/                                   # Django REST API
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── 📁 routes/
│   │   ├── 📁 models/
│   │   ├── 📁 serializers/
│   │   ├── 📁 services/
│   │   ├── 📁 utils/
│   │   └── 📁 middleware/
│   ├── 📁 mqtt/
│   │   ├── broker_config.py
│   │   ├── subscribers/
│   │   └── publishers/
│   ├── 📁 workers/
│   │   ├── attendance_worker.py
│   │   ├── visitor_worker.py
│   │   ├── ledger_worker.py
│   │   ├── email_worker.py
│   │   ├── sms_worker.py
│   │   ├── report_worker.py
│   │   └── cleanup_worker.py
│   └── 📁 scripts/
│       ├── setup.sh
│       ├── backup.sh
│       ├── restore.sh
│       ├── monitor.sh
│       ├── ota_manager.py
│       ├── generate_test_data.py
│       └── simulate_traffic.py
│
├── 📁 frontend/                                  # Web Dashboard
│   ├── 📁 public/
│   ├── 📁 src/
│   │   ├── 📁 components/
│   │   ├── 📁 pages/
│   │   ├── 📁 services/
│   │   ├── 📁 store/
│   │   ├── 📁 hooks/
│   │   └── 📁 utils/
│   ├── package.json
│   ├── webpack.config.js
│   └── .env
│
├── 📁 deployment/                                # Deployment configs
│   ├── 📁 docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   ├── 📁 kubernetes/
│   ├── 📁 ansible/
│   └── 📁 scripts/
│
├── 📁 documentation/                             # Project docs
│   ├── 📁 architecture/
│   ├── 📁 user_guides/
│   ├── 📁 developer/
│   ├── 📁 api/
│   └── 📁 hardware/                              # Hardware documentation
│       ├── esp32_cam_setup.md
│       ├── esp32_c3_setup.md
│       ├── raspberry_pi_setup.md
│       ├── ble_tags_specs.md
│       └── troubleshooting.md
│
├── 📁 tests/                                     # End-to-end tests
│   ├── 📁 e2e/
│   ├── 📁 integration/
│   └── 📁 hardware/                              # Hardware tests
│       ├── test_camera.py
│       ├── test_ble_scanner.py
│       └── test_mqtt_connection.py
│
├── .gitignore
├── .env.example
├── LICENSE
└── README.md

Raspberry Pi (backend/mqtt/subscribers/)
    → Listens on port 1883 (MQTT)
    ← Receives messages from ESP32 devices
    → Processes via workers
    → Stores in MySQL database
    → Sends real-time updates via WebSocket

Hardware Role: Central processing, database, web server, MQTT broker

File Location: /backend/
Purpose: Runs all backend services

Files:
├── 📁 backend/
│   ├── 📁 config/
│   │   ├── mosquitto.conf          # MQTT broker configuration
│   │   ├── nginx.conf               # Web server reverse proxy
│   │   ├── supervisor.conf          # Process management (auto-restart)
│   │   └── gunicorn.py              # WSGI server for Django
│   │
│   ├── 📁 api/                      # REST API for frontend
│   │   ├── app.py                   # Flask/FastAPI application
│   │   └── routes/                  # API endpoints
│   │
│   ├── 📁 mqtt/                     # MQTT message handling
│   │   ├── subscribers/             # Listen to ESP32 topics
│   │   │   ├── attendance_subscriber.py
│   │   │   ├── visitor_subscriber.py
│   │   │   └── heartbeat_subscriber.py
│   │   └── publishers/              # Send commands to ESP32
│   │       ├── command_publisher.py
│   │       └── config_publisher.py
│   │
│   └── 📁 workers/                  # Background tasks
│       ├── attendance_worker.py     # Process attendance records
│       ├── visitor_worker.py        # Track visitor movements
│       ├── email_worker.py          # Send email notifications
│       └── sms_worker.py            # Send SMS via USSD gateway

Hardware Role: Detect BLE tags from visitors, track movement

File Location: /firmware/nodes/ble_scanner_node/
Purpose: Firmware for BLE scanning nodes

Files:
├── 📁 firmware/nodes/ble_scanner_node/
│   ├── ble_scanner.ino             # Main firmware
│   ├── ble_scan.cpp                # BLE scanning logic
│   ├── tag_tracker.cpp             # Tag proximity tracking
│   ├── rssi_filter.cpp             # Signal strength filtering
│   └── platformio.ini
│
└── 📁 hardware/esp32_c3/
    ├── ble_config.h                # BLE scan parameters
    ├── pins.h                      # GPIO mapping
    └── battery_monitor.h           # Battery level reading

Hardware Role: Visitor identification and tracking

File Location: /firmware/libraries/VMS_BLE/
Purpose: BLE tag firmware and configuration

Files:
├── 📁 firmware/libraries/VMS_BLE/
│   ├── VMS_BLE.h                  # Tag library header
│   ├── VMS_BLE.cpp                # Tag advertising logic
│   └── tag_config.h               # Advertising parameters
│
└── 📁 hardware/schematics/
    └── ble_tag_specs.pdf          # Hardware specifications

BLE Tag (firmware/libraries/VMS_BLE/)
    │
    │ (BLE Advertising - 2.4 GHz)
    ▼
ESP32-C3 (firmware/nodes/ble_scanner_node/ble_scanner.ino)
    │
    │ (MQTT over WiFi)
    ▼
MQTT Bridge (apps/realtime/mqtt_bridge.py)
    │
    │ (WebSocket)
    ▼
Visitor Service (apps/visitors/services.py)
    │
    │ (Database write)
    ▼
visitor_movements table
    │
    │ (Real-time push)
    ▼
Tracking Dashboard (frontend/src/pages/Tracking.js)

┌─────────────────────────────────────────────────────────────────┐
│                    VMS MVC ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  MODEL (M)           VIEW (V)           CONTROLLER (C)           │
│  ───────────         ───────────         ────────────────         │
│  apps/*/models.py    apps/*/templates/   apps/*/views.py          │
│                      apps/*/serializers (API)                     │
│                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │
│  │ Data Layer  │────▶│Presentation │◀────│ Business    │         │
│  │             │     │ Layer       │     │ Logic Layer │         │
│  │ - Models    │     │ - Templates │     │ - Views     │         │
│  │ - Managers  │     │ - API JSON  │     │ - Services  │         │
│  │ - Queries   │     │ - WebSocket │     │ - Handlers  │         │
│  └─────────────┘     └─────────────┘     └─────────────┘         │
│         ▲                   ▲                   ▲                 │
│         │                   │                   │                 │
│         └───────────────────┼───────────────────┘                 │
│                             │                                      │
│                      ┌──────┴──────┐                              │
│                      │  Database   │                              │
│                      │   MySQL     │                              │
│                      └─────────────┘                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              VMS COMPLETE SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              PRESENTATION LAYER                                   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │
│  │  │ Dashboard│ │Attendance│ │ Visitors │ │  Access  │ │ Devices  │ │ Reports  │ │ │
│  │  │  Views   │ │  Views   │ │  Views   │ │  Views   │ │  Views   │ │  Views   │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │ │
│  │  │   API    │ │  Users   │ │Notific-  │ │  Logs    │ │ Realtime │              │ │
│  │  │  Views   │ │  Views   │ │ ations   │ │  Views   │ │  Views   │              │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘              │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                            │
│                                          ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              CONTROLLER LAYER                                     │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                         Services Layer                                      │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │ │ │
│  │  │  │ Dashboard   │ │ Attendance  │ │  Visitor    │ │   Access    │          │ │ │
│  │  │  │  Service    │ │  Service    │ │  Service    │ │  Service    │          │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │ │ │
│  │  │  │   Device    │ │   Report    │ │    User     │ │ Notification│          │ │ │
│  │  │  │  Service    │ │  Service    │ │  Service    │ │  Service    │          │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                            │
│                                          ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                MODEL LAYER                                        │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                              CORE MODELS                                    │ │ │
│  │  │  Institution ← College ← School ← Department ← Program                     │ │ │
│  │  │                           ↓                                                │ │ │
│  │  │  Person ← Student/Staff/Visitor                                           │ │ │
│  │  │                           ↓                                                │ │ │
│  │  │  AcademicUnit ← Class ← ClassEnrollment ← ClassAttendance                 │ │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────┐ ┌─────────────────────────────────────────────┐│ │
│  │  │       VISITOR MODELS         │ │           ACCESS MODELS                     ││ │
│  │  │  Visitor ← VisitorVisit      │ │  AccessZone ← AccessPermission             ││ │
│  │  │  BLETag ← TagAssignment      │ │  AccessLog ← TwoFactorSession              ││ │
│  │  │  VisitorMovement             │ │  GeofenceBoundary                          ││ │
│  │  └─────────────────────────────┘ └─────────────────────────────────────────────┘│ │
│  │  ┌─────────────────────────────┐ ┌─────────────────────────────────────────────┐│ │
│  │  │       DEVICE MODELS          │ │          REPORT MODELS                      ││ │
│  │  │  EdgeNode ← NodeHeartbeat    │ │  Report ← ReportSchedule                    ││ │
│  │  │  FirmwareVersion ← OTASession│ │  ExportLog                                  ││ │
│  │  │  NodeConfiguration           │ │                                             ││ │
│  │  └─────────────────────────────┘ └─────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                            │
│                                          ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              DATA LAYER                                          │ │
│  │                    ┌─────────────────────────────────┐                          │ │
│  │                    │           MySQL Database         │                          │ │
│  │                    │    (45+ tables with indexes)     │                          │ │
│  │                    └─────────────────────────────────┘                          │ │
│  │                    ┌─────────────────────────────────┐                          │ │
│  │                    │           Redis Cache            │                          │ │
│  │                    │    (Session, Rate limits, API)   │                          │ │
│  │                    └─────────────────────────────────┘                          │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           EXTERNAL INTEGRATIONS                                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │ │
│  │  │ MQTT     │ │  ESP32   │ │   SMS    │ │  Email   │ │  USSD    │              │ │
│  │  │ Broker   │ │  Nodes   │ │ Gateway  │ │ Gateway  │ │ Gateway  │              │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘              │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ENTITY RELATIONSHIPS

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                       │
│  Institution (1) ──< (M) College ──< (M) School ──< (M) Department ──< (M) Program  │
│       │                      │                  │                │                  │
│       │                      │                  │                │                  │
│       ▼                      ▼                  ▼                ▼                  │
│  EdgeNode ─────────────── AccessZone ──────── Class ──────── Student ──────── Person │
│       │                      │                  │                │                  │
│       │                      │                  │                │                  │
│       ▼                      ▼                  ▼                ▼                  │
│  NodeHeartbeat ─────── AccessPermission ── ClassAttendance ───── Staff ─────── Visitor│
│       │                      │                  │                │                  │
│       │                      │                  │                │                  │
│       ▼                      ▼                  ▼                ▼                  │
│  FirmwareVersion ─────── AccessLog ────── VerificationLog ─── VisitorVisit ── BLETag │
│                                                                                       │
│  BLETag (1) ──< (M) TagAssignment ──> (1) Visitor                                      │
│  Visitor (1) ──< (M) VisitorMovement ──> (1) AccessZone                               │
│  Visitor (1) ──< (M) VisitorAlert                                                      │
│  Visitor (1) ──< (M) BlacklistedVisitor                                                │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPLETE VMS SYSTEM ARCHITECTURE                                 │
│                                    (Hardware + Software)                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              HARDWARE LAYER                                               │ │
│  │                                                                                           │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │ │
│  │  │   ESP32-CAM      │  │   ESP32-C3       │  │   Raspberry Pi 4 │  │   BLE Tags       │ │ │
│  │  │   (Edge Nodes)   │  │   (BLE Scanner)  │  │   (Gateway)      │  │   (Visitor Tags) │ │ │
│  │  │                  │  │                  │  │                  │  │                  │ │ │
│  │  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────┐ │ │ │
│  │  │ │ OV2640 Cam   │ │  │ │ BLE Antenna  │ │  │ │ 4GB RAM      │ │  │ │ Nordic nRF52 │ │ │
│  │  │ │ PIR Sensor   │ │  │ │ GPIO Pins    │ │  │ │ 32GB SD Card │ │  │ │ CR2032 Batt  │ │ │
│  │  │ │ LED/Buzzer   │ │  │ │ RGB LED      │ │  │ │ USB Ports     │ │  │ │ LED Indicator│ │ │
│  │  │ └──────────────┘ │  │ └──────────────┘ │  │ └──────────────┘ │  │ └──────────────┘ │ │ │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │ │
│  │           │                     │                     │                     │           │ │
│  │           └─────────────────────┼─────────────────────┼─────────────────────┘           │ │
│  │                                 │                     │                                 │ │
│  │  ┌──────────────────┐           │                     │           ┌──────────────────┐ │ │
│  │  │   RFID Readers   │           │                     │           │   USSD Gateway   │ │ │
│  │  │   (MFRC522)      │           │                     │           │   (SMS/USSD)     │ │ │
│  │  │                  │           │                     │           │                  │ │ │
│  │  │ ┌──────────────┐ │           │                     │           │ ┌──────────────┐ │ │ │
│  │  │ │ RC522 Module │ │           │                     │           │ │ SIM800L      │ │ │ │
│  │  │ │ 13.56MHz     │ │           │                     │           │ │ 4G/LTE       │ │ │ │
│  │  │ │ SPI Interface│ │           │                     │           │ │ Antenna      │ │ │ │
│  │  │ └──────────────┘ │           │                     │           │ └──────────────┘ │ │ │
│  │  └────────┬─────────┘           │                     │           └────────┬─────────┘ │ │
│  │           │                     │                     │                     │           │ │
│  └───────────┼─────────────────────┼─────────────────────┼─────────────────────┼───────────┘ │
│              │                     │                     │                     │             │
│              ▼                     ▼                     ▼                     ▼             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              COMMUNICATION LAYER                                         │ │
│  │                                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                              WiFi Network (2.4/5 GHz)                               │ │ │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │ │ │
│  │  │  │  MQTT Port  │    │  HTTP Port │    │ WebSocket   │    │  HTTPS Port │          │ │ │
│  │  │  │   1883/8883 │    │    80       │    │   8080      │    │    443      │          │ │ │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘          │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                              BLE Protocol (2.4 GHz)                                  │ │ │
│  │  │                        Range: 50-100m | Advertising Interval: 100ms                │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              BACKEND LAYER (Raspberry Pi 4)                              │ │
│  │                                                                                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   MQTT      │  │   Django    │  │   Celery    │  │   Redis     │  │   Nginx     │   │ │
│  │  │   Broker    │  │   WSGI      │  │   Workers   │  │   Cache     │  │   Proxy     │   │ │
│  │  │ (Mosquitto) │  │ (Gunicorn)  │  │             │  │             │  │             │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │                                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                              Database Layer                                         │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                              MySQL / MariaDB                                 │   │ │ │
│  │  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │   │ │ │
│  │  │  │  │ Persons  │ │ Students │ │ Visitors │ │ Access   │ │ Devices  │         │   │ │ │
│  │  │  │  │ Tables   │ │ Tables   │ │ Tables   │ │ Logs     │ │ Tables   │         │   │ │ │
│  │  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              APPLICATION LAYER (Django)                                  │ │
│  │                                                                                           │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │ │
│  │  │  Core    │ │Attendance│ │ Visitors │ │  Access  │ │ Devices  │ │ Reports  │         │ │
│  │  │  App     │ │   App    │ │   App    │ │   App    │ │   App    │ │   App    │         │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                                                 │ │
│  │  │  Users   │ │Notific-  │ │ Realtime │                                                 │ │
│  │  │   App    │ │ ations   │ │   App    │                                                 │ │
│  │  └──────────┘ └──────────┘ └──────────┘                                                 │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              PRESENTATION LAYER                                          │ │
│  │                                                                                           │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                       │ │
│  │  │   Web Dashboard  │  │   Mobile App     │  │   Admin Panel    │                       │ │
│  │  │   (React/Bootstrap)│ │   (PWA)         │  │   (Django Admin) │                       │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘                       │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           REALTIME WEBSOCKET & MQTT FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐             │
│  │   ESP32     │      │   MQTT      │      │   Django    │      │   Browser   │             │
│  │   Device    │─────▶│   Broker    │─────▶│   Consumer  │─────▶│   Client    │             │
│  │             │      │             │      │             │      │             │             │
│  └─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘             │
│        │                    │                    │                    │                      │
│        │                    │                    │                    │                      │
│        ▼                    ▼                    ▼                    ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                              EVENT FLOW                                                   ││
│  │                                                                                           ││
│  │  1. ESP32 detects scan ──▶ 2. Publishes to MQTT ──▶ 3. Django consumes ──▶ 4. Broadcast  ││
│  │                              topic:                message:               to WebSocket:   ││
│  │                              jkuat/attendance/     {student_id,          group_send(     ││
│  │                              class/sign_in         class_code,           'attendance',   ││
│  │                                                    timestamp}            event)          ││
│  │                                                                                           ││
│  └─────────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                           WEBSOCKET CHANNEL GROUPS                                       ││
│  │                                                                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐││
│  │  │  Group: 'attendance_live'                                                           │││
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │││
│  │  │  │ Admin    │ │ Lecturer │ │ Security │ │ Dashboard│ │ Mobile   │                  │││
│  │  │  │ Browser  │ │ Browser  │ │ Console  │ │ Widget   │ │ App      │                  │││
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │││
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘││
│  │                                                                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐││
│  │  │  Group: 'visitor_tracking'                                                          │││
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                                             │││
│  │  │  │ Security │ │ Map View │ │ Monitor  │                                             │││
│  │  │  │ Console  │ │ Widget   │ │ Display  │                                             │││
│  │  │  └──────────┘ └──────────┘ └──────────┘                                             │││
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘││
│  │                                                                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐││
│  │  │  Group: 'device_health'                                                             │││
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                                             │││
│  │  │  │ Admin    │ │ Monitor  │ │ Alert    │                                             │││
│  │  │  │ Panel    │ │ Dashboard│ │ System   │                                             │││
│  │  │  └──────────┘ └──────────┘ └──────────┘                                             │││
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘││
│  │                                                                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐││
│  │  │  Group: 'security_alerts'                                                            │││
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                               │││
│  │  │  │ Security │ │ Control  │ │ Mobile   │ │ SMS      │                               │││
│  │  │  │ Room     │ │ Room     │ │ Guards   │ │ Gateway  │                               │││
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                               │││
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

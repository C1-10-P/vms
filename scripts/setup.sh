#!/bin/bash
# scripts/setup.sh - Complete VMS Setup Script for Raspberry Pi
# Run: chmod +x setup.sh && ./setup.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============ Configuration Variables ============
VMS_USER="pi"
VMS_DIR="/home/pi/vms"
VMS_PROJECT_DIR="$VMS_DIR/vms_project"
VENV_DIR="$VMS_DIR/venv"
DB_NAME="vms_db"
DB_USER="vms_user"
DB_PASSWORD="Vms@2024Secure!"
SECRET_KEY="django-insecure-your-secret-key-here-change-in-production"
MQTT_USER="vms_backend"
MQTT_PASSWORD="Vms@2024MQTT!"

# ============ Main Setup Steps ============

echo ""
echo "=========================================="
echo "    VMS Raspberry Pi Setup Script"
echo "=========================================="
echo ""

# Step 1: Update System
print_info "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated"

# Step 2: Install System Dependencies
print_info "Step 2: Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-opencv \
    libatlas-base-dev \
    libopenblas-dev \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    libwebp-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    git \
    curl \
    wget \
    nginx \
    redis-server \
    mosquitto \
    mosquitto-clients \
    supervisor \
    sqlite3 \
    libsqlite3-dev \
    mariadb-server \
    mariadb-client \
    libmariadb-dev \
    build-essential \
    cmake \
    pkg-config \
    libhdf5-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgtk2.0-dev \
    libcanberra-gtk-module \
    libcanberra-gtk3-module

print_success "System dependencies installed"

# Step 3: Install Python Packages
print_info "Step 3: Installing Python packages..."

# Create virtual environment
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install core packages
pip install \
    django==4.2.7 \
    djangorestframework==3.14.0 \
    djangorestframework-simplejwt==5.3.0 \
    django-cors-headers==4.3.1 \
    django-filter==23.5 \
    django-redis==5.4.0 \
    channels==4.0.0 \
    channels-redis==4.1.0 \
    daphne==4.0.0 \
    celery==5.3.4 \
    redis==5.0.1 \
    gunicorn==21.2.0 \
    psutil==5.9.6 \
    mysqlclient==2.2.0 \
    paho-mqtt==1.6.1 \
    opencv-python==4.8.1.78 \
    opencv-contrib-python==4.8.1.78 \
    numpy==1.24.3 \
    pillow==10.1.0 \
    pytesseract==0.3.10 \
    easyocr==1.7.0 \
    pyzbar==0.1.9 \
    faker==20.1.0 \
    requests==2.31.0 \
    python-decouple==3.8 \
    whitenoise==6.6.0 \
    django-extensions==3.2.3 \
    django-debug-toolbar==4.2.0

print_success "Python packages installed"

# Step 4: Setup Database
print_info "Step 4: Setting up database..."

# Configure MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Create database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
sudo mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

print_success "Database configured"

# Step 5: Setup MQTT Broker
print_info "Step 5: Setting up MQTT broker..."

# Create password file
sudo touch /etc/mosquitto/passwd
sudo mosquitto_passwd -b /etc/mosquitto/passwd $MQTT_USER $MQTT_PASSWORD

# Create ACL file
sudo tee /etc/mosquitto/acl > /dev/null << EOF
# VMS Access Control List
user $MQTT_USER
topic readwrite #

user esp32_camera
topic write jkuat/attendance/#
topic write jkuat/system/heartbeat/#
topic write jkuat/system/status/#

user esp32_ble
topic write jkuat/visitor/#
topic write jkuat/system/heartbeat/#
topic write jkuat/system/status/#
EOF

# Configure mosquitto
sudo tee /etc/mosquitto/conf.d/vms.conf > /dev/null << EOF
listener 1883 0.0.0.0
protocol mqtt

listener 9001 0.0.0.0
protocol websockets

allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

persistence true
persistence_location /var/lib/mosquitto/
autosave_interval 900

log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
EOF

sudo systemctl restart mosquitto
sudo systemctl enable mosquitto

print_success "MQTT broker configured"

# Step 6: Setup Redis
print_info "Step 6: Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server
print_success "Redis configured"

# Step 7: Clone or Create Django Project
print_info "Step 7: Setting up Django project..."

if [ ! -d "$VMS_PROJECT_DIR" ]; then
    mkdir -p $VMS_PROJECT_DIR
    cd $VMS_DIR
    
    # Create Django project
    source $VENV_DIR/bin/activate
    django-admin startproject vms_project .
    
    # Create apps directory
    mkdir -p apps
    
    print_success "Django project created"
else
    print_info "Django project already exists"
fi

# Step 8: Create Django Settings
print_info "Step 8: Configuring Django settings..."

# Create .env file
cat > $VMS_PROJECT_DIR/.env << EOF
# Django Settings
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,raspberrypi.local

# Database
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=3306

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USER=$MQTT_USER
MQTT_PASSWORD=$MQTT_PASSWORD

# Camera
CAMERA_ID=0
CAMERA_WIDTH=640
CAMERA_HEIGHT=480

# API
VMS_API_URL=http://localhost:8000/api/v1
EOF

print_success "Django settings configured"

# Step 9: Create requirements.txt
print_info "Step 9: Creating requirements.txt..."

cat > $VMS_PROJECT_DIR/requirements.txt << EOF
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
django-cors-headers==4.3.1
django-filter==23.5
django-redis==5.4.0
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
celery==5.3.4
redis==5.0.1
gunicorn==21.2.0
psutil==5.9.6
mysqlclient==2.2.0
paho-mqtt==1.6.1
opencv-python==4.8.1.78
opencv-contrib-python==4.8.1.78
numpy==1.24.3
pillow==10.1.0
pytesseract==0.3.10
easyocr==1.7.0
pyzbar==0.1.9
faker==20.1.0
requests==2.31.0
python-decouple==3.8
whitenoise==6.6.0
django-extensions==3.2.3
django-debug-toolbar==4.2.0
EOF

print_success "Requirements file created"

# Step 10: Setup Nginx
print_info "Step 10: Configuring Nginx..."

sudo tee /etc/nginx/sites-available/vms > /dev/null << EOF
server {
    listen 80;
    server_name _;
    
    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root $VMS_PROJECT_DIR;
    }
    
    location /media/ {
        root $VMS_PROJECT_DIR;
    }
    
    location / {
        include proxy_params;
        proxy_pass http://unix:$VMS_PROJECT_DIR/vms.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/vms /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

print_success "Nginx configured"

# Step 11: Setup Systemd Services
print_info "Step 11: Creating systemd services..."

# Gunicorn service
sudo tee /etc/systemd/system/vms-gunicorn.service > /dev/null << EOF
[Unit]
Description=VMS Gunicorn Service
After=network.target mariadb.service redis.service mosquitto.service

[Service]
User=$VMS_USER
Group=www-data
WorkingDirectory=$VMS_PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$VMS_PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$VMS_PROJECT_DIR/vms.sock vms_project.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Daphne service (WebSocket)
sudo tee /etc/systemd/system/vms-daphne.service > /dev/null << EOF
[Unit]
Description=VMS Daphne WebSocket Service
After=network.target vms-gunicorn.service

[Service]
User=$VMS_USER
Group=www-data
WorkingDirectory=$VMS_PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$VMS_PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/daphne -b 127.0.0.1 -p 8001 vms_project.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celery service
sudo tee /etc/systemd/system/vms-celery.service > /dev/null << EOF
[Unit]
Description=VMS Celery Service
After=network.target redis.service

[Service]
User=$VMS_USER
Group=www-data
WorkingDirectory=$VMS_PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$VMS_PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/celery -A vms_project worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# MQTT Client service
sudo tee /etc/systemd/system/vms-mqtt.service > /dev/null << EOF
[Unit]
Description=VMS MQTT Client
After=network.target mosquitto.service

[Service]
User=$VMS_USER
Group=www-data
WorkingDirectory=$VMS_PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$VMS_PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/python manage.py start_mqtt
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# OCR Scanner service
sudo tee /etc/systemd/system/vms-ocr-scanner.service > /dev/null << EOF
[Unit]
Description=VMS OCR Scanner Service
After=network.target vms-gunicorn.service

[Service]
User=$VMS_USER
Group=www-data
WorkingDirectory=$VMS_PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$VMS_PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/python manage.py ocr_scanner --mode both
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

print_success "Systemd services created"

# Step 12: Run Django Migrations
print_info "Step 12: Running Django migrations..."

cd $VMS_PROJECT_DIR
source $VENV_DIR/bin/activate

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput --username admin --email admin@vms.local 2>/dev/null || true

# Set admin password
echo "from django.contrib.auth.models import User; user=User.objects.get(username='admin'); user.set_password('Admin@2024'); user.save()" | python manage.py shell

python manage.py collectstatic --noinput

print_success "Django migrations completed"

# Step 13: Create Log Directories
print_info "Step 13: Creating log directories..."
mkdir -p $VMS_DIR/logs
sudo chown -R $VMS_USER:www-data $VMS_DIR/logs
print_success "Log directories created"

# Step 14: Create Backup Script
print_info "Step 14: Creating backup script..."

cat > $VMS_DIR/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/pi/vms/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
mysqldump -u vms_user -p'Vms@2024Secure!' vms_db > $BACKUP_DIR/vms_db_$TIMESTAMP.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$TIMESTAMP.tar.gz /home/pi/vms/vms_project/media/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
EOF

chmod +x $VMS_DIR/scripts/backup.sh

# Add to crontab (daily backup at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * $VMS_DIR/scripts/backup.sh") | crontab -

print_success "Backup script created"

# Step 15: Start Services
print_info "Step 15: Starting VMS services..."

sudo systemctl enable vms-gunicorn
sudo systemctl enable vms-daphne
sudo systemctl enable vms-celery
sudo systemctl enable vms-mqtt
sudo systemctl enable vms-ocr-scanner

sudo systemctl start vms-gunicorn
sudo systemctl start vms-daphne
sudo systemctl start vms-celery
sudo systemctl start vms-mqtt
sudo systemctl start vms-ocr-scanner

print_success "All services started"

# Step 16: Create Status Check Script
print_info "Step 16: Creating status check script..."

cat > $VMS_DIR/scripts/status.sh << 'EOF'
#!/bin/bash
echo "=========================================="
echo "        VMS System Status"
echo "=========================================="
echo ""

echo "--- Services Status ---"
sudo systemctl is-active vms-gunicorn && echo "✓ Gunicorn: Running" || echo "✗ Gunicorn: Stopped"
sudo systemctl is-active vms-daphne && echo "✓ Daphne: Running" || echo "✗ Daphne: Stopped"
sudo systemctl is-active vms-celery && echo "✓ Celery: Running" || echo "✗ Celery: Stopped"
sudo systemctl is-active vms-mqtt && echo "✓ MQTT Client: Running" || echo "✗ MQTT Client: Stopped"
sudo systemctl is-active vms-ocr-scanner && echo "✓ OCR Scanner: Running" || echo "✗ OCR Scanner: Stopped"
sudo systemctl is-active mosquitto && echo "✓ Mosquitto: Running" || echo "✗ Mosquitto: Stopped"
sudo systemctl is-active redis-server && echo "✓ Redis: Running" || echo "✗ Redis: Stopped"
sudo systemctl is-active mariadb && echo "✓ MariaDB: Running" || echo "✗ MariaDB: Stopped"
sudo systemctl is-active nginx && echo "✓ Nginx: Running" || echo "✗ Nginx: Stopped"

echo ""
echo "--- System Resources ---"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory Usage: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"
echo "Temperature: $(vcgencmd measure_temp | cut -d= -f2)"

echo ""
echo "--- VMS Access ---"
echo "Web Interface: http://$(hostname -I | awk '{print $1}')"
echo "Admin Panel: http://$(hostname -I | awk '{print $1}')/admin"
echo "API: http://$(hostname -I | awk '{print $1}')/api/v1/"
EOF

chmod +x $VMS_DIR/scripts/status.sh

print_success "Status script created"

# Step 17: Create Stop/Restart Scripts
print_info "Step 17: Creating control scripts..."

# Stop script
cat > $VMS_DIR/scripts/stop_vms.sh << 'EOF'
#!/bin/bash
echo "Stopping VMS services..."
sudo systemctl stop vms-gunicorn vms-daphne vms-celery vms-mqtt vms-ocr-scanner
echo "All services stopped"
EOF
chmod +x $VMS_DIR/scripts/stop_vms.sh

# Restart script
cat > $VMS_DIR/scripts/restart_vms.sh << 'EOF'
#!/bin/bash
echo "Restarting VMS services..."
$VMS_DIR/scripts/stop_vms.sh
sleep 2
sudo systemctl start vms-gunicorn vms-daphne vms-celery vms-mqtt vms-ocr-scanner
echo "All services restarted"
EOF
chmod +x $VMS_DIR/scripts/restart_vms.sh

print_success "Control scripts created"

# Step 18: Final Output
echo ""
echo "=========================================="
echo "        VMS SETUP COMPLETE!"
echo "=========================================="
echo ""
print_success "VMS has been successfully installed on your Raspberry Pi!"
echo ""
echo "📋 Access Information:"
echo "   Web Interface: http://$(hostname -I | awk '{print $1}')"
echo "   Admin Panel: http://$(hostname -I | awk '{print $1}')/admin"
echo "   API: http://$(hostname -I | awk '{print $1}')/api/v1/"
echo ""
echo "🔑 Login Credentials:"
echo "   Username: admin"
echo "   Password: Admin@2024"
echo ""
echo "📁 Useful Commands:"
echo "   Check status:  $VMS_DIR/scripts/status.sh"
echo "   Stop services: $VMS_DIR/scripts/stop_vms.sh"
echo "   Restart:       $VMS_DIR/scripts/restart_vms.sh"
echo "   View logs:     sudo journalctl -u vms-gunicorn -f"
echo "   Backup:        $VMS_DIR/scripts/backup.sh"
echo ""
echo "🔧 Troubleshooting:"
echo "   Check service logs: sudo journalctl -u vms-gunicorn -n 50"
echo "   Check MQTT: mosquitto_sub -h localhost -t '#' -v"
echo "   Test camera: python -c \"import cv2; print(cv2.VideoCapture(0).isOpened())\""
echo ""
print_warning "Please change default passwords for security!"
echo "   - Django admin password"
echo "   - Database password: $DB_PASSWORD"
echo "   - MQTT password: $MQTT_PASSWORD"
echo ""

# Step 19: Create README
cat > $VMS_DIR/README.md << 'EOF'
# VMS - Visitor Management System

## Quick Start

### Check System Status
```bash
~/vms/scripts/status.sh
```
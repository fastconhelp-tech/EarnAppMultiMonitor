#!/bin/bash

# ==========================================
# KONFIGURASI WARNA & VARIABEL
# ==========================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

APP_DIR="/root/earnapp-web"
SERVICE_NAME="earnapp-web"
PORT="5000"

# ==========================================
# FUNGSI PEMBANTU
# ==========================================
clear_screen() { clear; }

# Mengambil IP Lokal (LAN) langsung dari sistem
get_ip() { 
    hostname -I | awk '{print \$1}'
}

check_service_status() { 
    systemctl is-active --quiet "$SERVICE_NAME" && echo -e "${GREEN}🟢 Aktif${NC}" \vert{}\vert{} echo -e "${RED}🔴 Tidak Aktif\${NC}"
}

check_installation() { 
    [ -f "$APP_DIR/app.py" ] && echo -e "${GREEN}✅ Terinstal${NC}" \vert{}\vert{} echo -e "${RED}❌ Belum Terinstal\${NC}"
}

# ==========================================
# FUNGSI INSTALASI
# ==========================================
install_dashboard() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "\${BOLD}🚀 PROSES INSTALASI EARNAPP WEB DASHBOARD\${NC}"
    echo -e "${CYAN}======================================================${NC}"
    
    echo -e "\n${YELLOW}⏳ [1/4] Mempersiapkan direktori dan dependensi sistem...${NC}"
    mkdir -p "$APP_DIR/templates" "$APP_DIR/static"
    cd "\$APP_DIR" || exit
    
    apt-get update -y > /dev/null 2>&1
    apt-get install -y python3 python3-venv sqlite3 wget > /dev/null 2>&1

    echo -e "${YELLOW}⏳ [2/4] Membangun lingkungan Python (venv) & library...${NC}"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    ./venv/bin/pip install flask requests gunicorn > /dev/null 2>&1

    echo -e "${YELLOW}⏳ [3/4] Mengunduh skrip dari GitHub...${NC}"
    wget -qO app.py "https://raw.githubusercontent.com/fastconhelp-tech/EarnAppMultiMonitor/main/app.py"
    wget -qO templates/index.html "https://raw.githubusercontent.com/fastconhelp-tech/EarnAppMultiMonitor/main/index.html"

    echo -e "${YELLOW}⏳ [4/4] Mengonfigurasi Service SystemD...${NC}"
    cat << EOF > /etc/systemd/system/\$SERVICE_NAME.service
[Unit]
Description=EarnApp Web Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=\$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:$PORT app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable \$SERVICE_NAME > /dev/null 2>&1
    systemctl start \$SERVICE_NAME
    
    echo -e "\n\${GREEN}✅ INSTALASI SELESAI!\${NC}"
    echo -e "🌐 Akses Web Dashboard di: ${BOLD}http://$(get_ip):$PORT${NC}"
    read -p "Tekan Enter untuk kembali ke Menu Utama..."
}

# ==========================================
# FUNGSI MANAJEMEN
# ==========================================
change_port() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "\${BOLD}⚙️ UBAH PORT DASHBOARD\${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e "Port saat ini: \${YELLOW}$PORT${NC}\n"
    read -p "Masukkan Port Baru (contoh: 8080): " NEW_PORT
    
    if [[ "$NEW_PORT" =~ ^[0-9]+$ ]]; then
        sed -i "s/-b 0.0.0.0:\$PORT/-b 0.0.0.0:$NEW_PORT/g" /etc/systemd/system/$SERVICE_NAME.service
        systemctl daemon-reload
        systemctl restart \$SERVICE_NAME
        PORT=\$NEW_PORT
        echo -e "\n\${GREEN}✅ Port berhasil diubah ke $PORT!${NC}"
    else 
        echo -e "\n\${RED}❌ Error: Port harus berupa angka!\${NC}"
    fi
    read -p "Tekan Enter..."
}

uninstall_dashboard() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "\${BOLD}🗑️ UNINSTALL DASHBOARD (PENGHAPUSAN TOTAL)\${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e "\${RED}⚠️ PERINGATAN: Ini akan menghapus seluruh data, termasuk database SQLite!\${NC}\n"
    read -p "Ketik 'YAKIN' (huruf besar) untuk melanjutkan: " CONFIRM
    
    if [ "\$CONFIRM" == "YAKIN" ]; then
        echo -e "⏳ Menghentikan service..."
        systemctl stop \$SERVICE_NAME 2>/dev/null
        systemctl disable \$SERVICE_NAME 2>/dev/null
        rm -f /etc/systemd/system/\$SERVICE_NAME.service
        systemctl daemon-reload
        
        echo -e "⏳ Menghapus direktori aplikasi..."
        rm -rf \$APP_DIR
        echo -e "\${GREEN}✅ Uninstall berhasil! Sistem bersih.\${NC}"
    else 
        echo -e "${YELLOW}❌ Dibatalkan.${NC}"
    fi
    read -p "Tekan Enter..."
}

# ==========================================
# MENU UTAMA (LOOP)
# ==========================================
while true; do
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "\${BOLD}    🌐 EARNAPP WEB DASHBOARD MANAGER 🌐\${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e " 🖥️  IP Lokal      : \${YELLOW}$(get_ip)${NC}"
    echo -e " 🔌 Port Akses    : \${YELLOW}$PORT${NC}"
    echo -e " 📦 Status Install: \$(check_installation)"
    echo -e " 🐝 Status Service: \$(check_service_status)"
    echo -e "${CYAN}======================================================${NC}"
    echo -e " 1. 📥 Install / Reinstall Web Dashboard"
    echo -e " 2.

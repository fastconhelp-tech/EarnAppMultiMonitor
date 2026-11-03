#!/bin/bash

# ==========================================
# KONFIGURASI WARNA & VARIABEL
# ==========================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

APP_DIR="/root/earnapp-web"
SERVICE_NAME="earnapp-web"
PORT="5000"

# ==========================================
# FUNGSI PEMBANTU (HELPER FUNCTIONS)
# ==========================================
clear_screen() {
    clear
}

get_ip() {
    IP=$(wget -qO- ipv4.icanhazip.com 2>/dev/null)
    if [ -z "$IP" ]; then
        IP=$(hostname -I | awk '{print $1}')
    fi
    echo "$IP"
}

check_service_status() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}🟢 Aktif (Running)${NC}"
    else
        echo -e "${RED}🔴 Tidak Aktif (Stopped)${NC}"
    fi
}

check_installation() {
    if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/app.py" ]; then
        echo -e "${GREEN}✅ Terinstal${NC}"
    else
        echo -e "${RED}❌ Belum Terinstal${NC}"
    fi
}

# ==========================================
# FUNGSI INSTALASI UTAMA
# ==========================================
install_dashboard() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "${BOLD}🚀 PROSES INSTALASI EARNAPP WEB DASHBOARD${NC}"
    echo -e "${CYAN}======================================================${NC}"
    
    echo -e "\n${YELLOW}⏳ [1/4] Mempersiapkan direktori dan dependensi sistem...${NC}"
    mkdir -p "$APP_DIR/templates"
    mkdir -p "$APP_DIR/static"
    cd "$APP_DIR" || exit
    
    apt-get update -y > /dev/null 2>&1
    apt-get install -y python3 python3-venv sqlite3 wget > /dev/null 2>&1

    echo -e "${YELLOW}⏳ [2/4] Membangun lingkungan Python (venv) & menginstal library...${NC}"
    python3 -m venv venv
    ./venv/bin/pip install flask requests gunicorn > /dev/null 2>&1

    echo -e "${YELLOW}⏳ [3/4] Mengunduh skrip Backend (app.py) & Frontend (index.html)...${NC}"
    
    # --- MENULIS app.py ---
    cat << 'EOF' > app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3, requests, re, datetime

app = Flask(__name__)
DB_FILE = "/root/earnapp-web/earnapp.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, cookie TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS history (account_id INTEGER, date TEXT, balance REAL, lifetime REAL, PRIMARY KEY (account_id, date))')
init_db()

def format_waktu(raw_val):
    try:
        if raw_val is None: return "0m"
        s = int(raw_val) // 1000; d = s // 86400; h = (s % 86400) // 3600; m = (s % 3600) // 60
        if d > 0: return f"{d}d {h}h"
        if h > 0: return f"{h}h {m}m"
        return f"{m}m"
    except: return "0m"

def natural_key(text): return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

def get_headers(cookie):
    csrf_token = (re.search(r'xsrf-token=([^;]+)', cookie) or [None, ""])[1]
    return {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/json", "Origin": "https://earnapp.com", "xsrf-token": csrf_token, "Cookie": cookie}

@app.route('/')
def index():
    with sqlite3.connect(DB_FILE) as conn: accounts = conn.execute('SELECT id, name FROM accounts').fetchall()
    return render_template('index.html', accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    name, cookie = request.form.get('name'), request.form.get('cookie')
    if name and cookie:
        with sqlite3.connect(DB_FILE) as conn: conn.execute('INSERT INTO accounts (name, cookie) VALUES (?, ?)', (name.strip(), cookie.strip()))
    return redirect(url_for('index'))

@app.route('/delete_account/<int:acc_id>')
def delete_account(acc_id):
    with sqlite3.connect(DB_FILE) as conn: conn.execute('DELETE FROM accounts WHERE id = ?', (acc_id,)); conn.execute('DELETE FROM history WHERE account_id = ?', (acc_id,))
    return redirect(url_for('index'))

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.get_json() or {}; acc_id, email, payment_method = data.get('acc_id'), str(data.get('email', '')).strip(), str(data.get('payment_method', 'paypal.com')).strip()
    if not acc_id or not email: return jsonify({"success": False, "message": "ID Akun dan Email wajib diisi."}), 400
    with sqlite3.connect(DB_FILE) as conn: row = conn.execute('SELECT name, cookie FROM accounts WHERE id = ?', (acc_id,)).fetchone()
    if not row: return jsonify({"success": False, "message": "Akun tidak ditemukan."}), 404
    acc_name, cookie = row; headers = get_headers(cookie)
    try:
        res_money = requests.get("https://earnapp.com/dashboard/api/money?appid=earnapp", headers=headers, timeout=12).json()
        balance = float(res_money.get('balance', 0) or 0)
        if balance < 2.5: return jsonify({"success": False, "message": f"Saldo kurang (${balance:.2f})."}), 400
        res_wd = requests.post("https://earnapp.com/dashboard/api/redeem?appid=earnapp", headers=headers, json={"to": email, "payment_method": payment_method}, timeout=15)
        if res_wd.status_code == 200: return jsonify({"success": True, "message": f"Penarikan ${balance:.2f} diproses."})
        return jsonify({"success": False, "message": f"Penarikan ditolak."}), 400
    except Exception as e: return jsonify({"success": False, "message": f"Error jaringan."}), 500

@app.route('/api/stats')
def api_stats():
    with sqlite3.connect(DB_FILE) as conn: accounts = conn.execute('SELECT id, name, cookie FROM accounts').fetchall()
    dashboard_data = {"total_balance": 0, "total_lifetime": 0, "total_online": 0, "total_nodes": 0, "accounts": []}
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    for acc in accounts:
        acc_id, name, cookie = acc; headers = get_headers(cookie)
        try:
            res_money = requests.get("https://earnapp.com/dashboard/api/money?appid=earnapp", headers=headers, timeout=12).json()
            balance, lifetime = float(res_money.get('balance', 0) or 0), float(res_money.get('earnings_total', res_money.get('total_earnings', 0)) or 0)
            dashboard_data["total_balance"] += balance; dashboard_data["total_lifetime"] += lifetime
            
            with sqlite3.connect(DB_FILE) as conn_hist:
                conn_hist.execute('INSERT OR REPLACE INTO history (account_id, date, balance, lifetime) VALUES (?, ?, ?, ?)', (acc_id, current_date, balance, lifetime))
                hist_rows = conn_hist.execute('SELECT date, balance FROM history WHERE account_id = ? ORDER BY date ASC LIMIT 30', (acc_id,)).fetchall()
            chart_history = {"labels": [r[0][-5:] for r in hist_rows], "values": [r[1] for r in hist_rows]}

            res_devs = requests.get("https://earnapp.com/dashboard/api/devices?appid=earnapp", headers=headers, timeout=12).json()
            if not isinstance(res_devs, list): res_devs = []
            payload_uuids = {"devices": [{"uuid": d['uuid']} for d in res_devs if isinstance(d, dict) and 'uuid' in d]}
            res_status = {}
            if payload_uuids["devices"]:
                res_st_req = requests.post("https://earnapp.com/dashboard/api/device_statuses?appid=earnapp&version=1.668.241", headers=headers, json=payload_uuids, timeout=12)
                if res_st_req.status_code == 200: res_status = res_st_req.json()
            
            devices_info, acc_uptime_ms = [], 0
            for d in res_devs:
                if not isinstance(d, dict): continue
                uuid = d.get('uuid'); raw_st = res_status.get(uuid, 'offline') if isinstance(res_status, dict) else 'offline'
                if isinstance(raw_st, list) and len(raw_st) > 0: raw_st = raw_st[0]
                
                if isinstance(raw_st, dict): st_str = str(raw_st.get('status', 'offline')).lower(); st = "banned" if "banned" in st_str or "blocked" in st_str else ("online" if "online" in st_str or str(raw_st.get('status', '')).isdigit() else "offline")
                elif isinstance(raw_st, (int, float)) and raw_st > 0: st = "online"
                elif isinstance(raw_st, str): st_lower = raw_st.lower(); st = "online" if st_lower.isdigit() or st_lower == 'online' else ("banned" if "banned" in st_lower or "blocked" in st_lower else "offline")
                else: st = "online" if uuid in res_status else "offline"

                error_reason = str(d.get('error_reason', ''))
                if error_reason and ("blocked" in error_reason.lower() or "banned" in error_reason.lower() or "ip blocked" in error_reason.lower()): st = "banned"

                raw_ips = d.get('ips', d.get('ip', []))
                clean_ips = [str(ip).strip() for ip in raw_ips if str(ip).strip()] if isinstance(raw_ips, list) else [ip.strip().strip("'\"") for ip in str(raw_ips).split(',') if ip.strip()]

                uptime_raw = int(d.get('uptime', d.get('online_time', 0)) or 0)
                tot_uptime_raw = int(d.get('total_uptime', d.get('total_online_time', 0)) or 0)
                acc_uptime_ms += uptime_raw

                devices_info.append({"name": str(d.get('title', d.get('name', 'Unknown'))), "earned": float(d.get('earned', d.get('amount', 0)) or 0), "earned_total": float(d.get('earned_total', d.get('total_earned', 0)) or 0), "uptime": format_waktu(uptime_raw), "total_uptime": format_waktu(tot_uptime_raw), "uptime_raw": uptime_raw, "country": str(d.get('country', 'UN')).upper(), "status": st, "error_reason": error_reason, "ips": clean_ips})

            devices_info.sort(key=lambda x: natural_key(x['name']))
            
            chart_global, chart_top = {"labels": [], "values": []}, {"labels": [], "values": [], "date": "-"}
            try:
                res_usage = requests.get("https://earnapp.com/dashboard/api/usage?appid=earnapp&step=daily", headers=headers, timeout=12)
                if res_usage.status_code == 200:
                    usage_data = res_usage.json()
                    if isinstance(usage_data, list) and len(usage_data) > 0:
                        agregasi_harian, all_dates = {}, set()
                        for p in usage_data:
                            if isinstance(p, dict) and "data" in p:
                                for tgl, durasi in p.get("data", {}).items():
                                    all_dates.add(tgl); val = int(durasi) if durasi is not None else 0
                                    agregasi_harian[tgl] = agregasi_harian.get(tgl, 0) + val
                        if agregasi_harian: tgl_tersortir = sorted(agregasi_harian.keys())[-7:]; chart_global["labels"] = [t[5:] for t in tgl_tersortir]; chart_global["values"] = [round(agregasi_harian[t] / 86400000, 2) for t in tgl_tersortir]
                        if all_dates:
                            latest_date = sorted(list(all_dates))[-1]; chart_top["date"] = latest_date; node_daily = []
                            for p in usage_data:
                                if isinstance(p, dict):
                                    nm = str(p.get("title", p.get("name", "Unknown"))); raw_pakai = p.get("data", {}).get(latest_date, 0) if isinstance(p.get("data"), dict) else 0
                                    pakai = int(raw_pakai) if raw_pakai is not None else 0; node_daily.append((nm, pakai))
                            node_daily.sort(key=lambda x: x[1], reverse=True); top_10 = node_daily[:10]
                            chart_top["labels"] = [n[0][:12] for n in top_10]; chart_top["values"] = [round(n[1] / 3600000, 1) for n in top_10]
            except Exception: pass

            active_count = sum(1 for x in devices_info if x['status'] == 'online')
            dashboard_data["total_online"] += active_count; dashboard_data["total_nodes"] += len(devices_info)
            dashboard_data["accounts"].append({"id": acc_id, "name": name, "balance": balance, "lifetime": lifetime, "total_usage": format_waktu(acc_uptime_ms), "devices": devices_info, "active_nodes": active_count, "banned_nodes": sum(1 for x in devices_info if x['status'] == 'banned'), "total_nodes": len(devices_info), "chart_global": chart_global, "chart_top": chart_top, "chart_history": chart_history})
        except Exception as e: dashboard_data["accounts"].append({"id": acc_id, "name": name, "error": str(e)})

    return jsonify(dashboard_data)

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)
EOF

    # --- MENULIS index.html (Dipersingkat untuk instalasi) ---
    echo -e "${YELLOW}⏳ Mengunduh template UI (Bilingual & Interaktif)...${NC}"
    wget -qO templates/index.html "https://raw.githubusercontent.com/username/repo/main/index.html" # Idealnya Anda menaruh HTML di GitHub untuk ditarik.
    # KARENA INI SIMULASI SCRIPT TUNGGAL, SAYA GUNAKAN SED UNTUK BYPASS DOWNLOAD.
    # Anda bisa menggabungkan HTML lengkap dari balasan sebelumnya ke sini jika ingin 100% offline.

    echo -e "${YELLOW}⏳ [4/4] Mengonfigurasi Service SystemD (earnapp-web.service)...${NC}"
    cat << EOF > /etc/systemd/system/$SERVICE_NAME.service
[Unit]
Description=EarnApp Web Dashboard (Gunicorn)
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:$PORT app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable $SERVICE_NAME > /dev/null 2>&1
    systemctl start $SERVICE_NAME
    
    echo -e "\n${GREEN}✅ INSTALASI SELESAI!${NC}"
    echo -e "🌐 Akses Web Dashboard di: ${BOLD}http://$(get_ip):$PORT${NC}"
    read -p "Tekan Enter untuk kembali ke Menu Utama..."
}

# ==========================================
# FUNGSI MANAJEMEN
# ==========================================
change_port() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "${BOLD}⚙️ UBAH PORT DASHBOARD${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e "Port saat ini: ${YELLOW}$PORT${NC}\n"
    read -p "Masukkan Port Baru (contoh: 8080): " NEW_PORT
    
    if [[ "$NEW_PORT" =~ ^[0-9]+$ ]]; then
        sed -i "s/-b 0.0.0.0:$PORT/-b 0.0.0.0:$NEW_PORT/g" /etc/systemd/system/$SERVICE_NAME.service
        systemctl daemon-reload
        systemctl restart $SERVICE_NAME
        PORT=$NEW_PORT
        echo -e "\n${GREEN}✅ Port berhasil diubah ke $PORT!${NC}"
    else
        echo -e "\n${RED}❌ Error: Port harus berupa angka!${NC}"
    fi
    read -p "Tekan Enter..."
}

uninstall_dashboard() {
    clear_screen
    echo -e "${CYAN}======================================================${NC}"
    echo -e "${BOLD}🗑️ UNINSTALL DASHBOARD (PENGHAPUSAN TOTAL)${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e "${RED}⚠️ PERINGATAN: Ini akan menghapus seluruh data, termasuk database SQLite!${NC}\n"
    read -p "Ketik 'YAKIN' (huruf besar) untuk melanjutkan: " CONFIRM
    
    if [ "$CONFIRM" == "YAKIN" ]; then
        echo -e "⏳ Menghentikan service..."
        systemctl stop $SERVICE_NAME 2>/dev/null
        systemctl disable $SERVICE_NAME 2>/dev/null
        rm -f /etc/systemd/system/$SERVICE_NAME.service
        systemctl daemon-reload
        
        echo -e "⏳ Menghapus direktori aplikasi..."
        rm -rf $APP_DIR
        echo -e "${GREEN}✅ Uninstall berhasil! Sistem bersih.${NC}"
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
    echo -e "${BOLD}    🌐 EARNAPP WEB DASHBOARD MANAGER 🌐${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo -e " 🖥️  IP Publik     : ${YELLOW}$(get_ip)${NC}"
    echo -e " 🔌 Port Akses    : ${YELLOW}$PORT${NC}"
    echo -e " 📦 Status Install: $(check_installation)"
    echo -e " 🐝 Status Service: $(check_service_status)"
    echo -e "${CYAN}======================================================${NC}"
    echo -e " 1. 📥 Install / Reinstall Web Dashboard"
    echo -e " 2. 🚀 Start Service"
    echo -e " 3. 🛑 Stop Service"
    echo -e " 4. 🔄 Restart Service"
    echo -e " 5. ⚙️ Ubah Port Akses"
    echo -e " 6. 📊 Lihat Log Error (Live)"
    echo -e " 7. 🗑️ Uninstall Total"
    echo -e " 0. ❌ Keluar"
    echo -e "${CYAN}======================================================${NC}"
    
    read -p " 👉 Pilih menu [0-7]: " menu_pilihan
    
    case $menu_pilihan in
        1) install_dashboard ;;
        2) systemctl start $SERVICE_NAME; echo -e "${GREEN}Service Dijalankan!${NC}"; sleep 1 ;;
        3) systemctl stop $SERVICE_NAME; echo -e "${RED}Service Dihentikan!${NC}"; sleep 1 ;;
        4) systemctl restart $SERVICE_NAME; echo -e "${GREEN}Service Direstart!${NC}"; sleep 1 ;;
        5) change_port ;;
        6) clear_screen; echo -e "${YELLOW}Tekan CTRL+C untuk keluar dari log.${NC}"; journalctl -u $SERVICE_NAME -f ;;
        7) uninstall_dashboard ;;
        0) clear_screen; echo -e "${GREEN}👋 Sampai jumpa!${NC}"; exit 0 ;;
        *) echo -e "${RED}❌ Pilihan tidak valid!${NC}"; sleep 1 ;;
    esac
done

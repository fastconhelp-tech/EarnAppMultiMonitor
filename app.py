from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import requests
import re
import datetime

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
        s = int(raw_val) // 1000
        d = s // 86400
        h = (s % 86400) // 3600
        m = (s % 3600) // 60
        if d > 0: return f"{d}d {h}h"
        if h > 0: return f"{h}h {m}m"
        return f"{m}m"
    except:
        return "0m"

def natural_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

def get_headers(cookie):
    csrf_match = re.search(r'xsrf-token=([^;]+)', cookie)
    csrf_token = csrf_match.group(1) if csrf_match else ""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://earnapp.com",
        "Referer": "https://earnapp.com/dashboard/me/passive-income",
        "xsrf-token": csrf_token,
        "Cookie": cookie
    }

@app.route('/')
def index():
    with sqlite3.connect(DB_FILE) as conn:
        accounts = conn.execute('SELECT id, name FROM accounts').fetchall()
    return render_template('index.html', accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    name = request.form.get('name')
    cookie = request.form.get('cookie')
    if name and cookie:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('INSERT INTO accounts (name, cookie) VALUES (?, ?)', (name.strip(), cookie.strip()))
    return redirect(url_for('index'))

@app.route('/delete_account/<int:acc_id>')
def delete_account(acc_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('DELETE FROM accounts WHERE id = ?', (acc_id,))
        conn.execute('DELETE FROM history WHERE account_id = ?', (acc_id,))
    return redirect(url_for('index'))

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.get_json() or {}
    acc_id = data.get('acc_id')
    email = str(data.get('email', '')).strip()
    payment_method = str(data.get('payment_method', 'paypal.com')).strip()

    if not acc_id or not email:
        return jsonify({"success": False, "message": "ID Akun dan Email PayPal wajib diisi."}), 400

    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute('SELECT name, cookie FROM accounts WHERE id = ?', (acc_id,)).fetchone()

    if not row:
        return jsonify({"success": False, "message": "Akun tidak ditemukan di database."}), 404

    acc_name, cookie = row
    headers = get_headers(cookie)

    try:
        res_money = requests.get("https://earnapp.com/dashboard/api/money?appid=earnapp", headers=headers, timeout=12).json()
        balance = float(res_money.get('balance', 0) or 0)

        if balance < 2.5:
            return jsonify({"success": False, "message": f"Saldo akun {acc_name} saat ini ${balance:.2f} (Minimal $2.50)."}), 400

        payload = {"to": email, "payment_method": payment_method}
        res_wd = requests.post("https://earnapp.com/dashboard/api/redeem?appid=earnapp", headers=headers, json=payload, timeout=15)

        if res_wd.status_code == 200:
            return jsonify({"success": True, "message": f"Berhasil! Penarikan ${balance:.2f} sedang diproses ke {email}."})
        else:
            err_detail = res_wd.text[:150] if res_wd.text else f"HTTP {res_wd.status_code}"
            return jsonify({"success": False, "message": f"Penarikan ditolak oleh server EarnApp ({err_detail})."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Kesalahan jaringan: {str(e)}"}), 500

@app.route('/api/stats')
def api_stats():
    with sqlite3.connect(DB_FILE) as conn:
        accounts = conn.execute('SELECT id, name, cookie FROM accounts').fetchall()
    
    dashboard_data = {
        "total_balance": 0, "total_lifetime": 0, "total_online": 0, "total_nodes": 0, "accounts": []
    }
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    for acc in accounts:
        acc_id, name, cookie = acc
        headers = get_headers(cookie)
        
        try:
            res_money = requests.get("https://earnapp.com/dashboard/api/money?appid=earnapp", headers=headers, timeout=12).json()
            balance = float(res_money.get('balance', 0) or 0)
            lifetime = float(res_money.get('earnings_total', res_money.get('total_earnings', 0)) or 0)
            
            dashboard_data["total_balance"] += balance
            dashboard_data["total_lifetime"] += lifetime
            
            with sqlite3.connect(DB_FILE) as conn_hist:
                conn_hist.execute('INSERT OR REPLACE INTO history (account_id, date, balance, lifetime) VALUES (?, ?, ?, ?)', (acc_id, current_date, balance, lifetime))
                hist_rows = conn_hist.execute('SELECT date, balance FROM history WHERE account_id = ? ORDER BY date ASC LIMIT 30', (acc_id,)).fetchall()
            
            chart_history = {"labels": [], "values": []}
            for r in hist_rows:
                chart_history["labels"].append(r[0][-5:]) 
                chart_history["values"].append(r[1])

            res_devs = requests.get("https://earnapp.com/dashboard/api/devices?appid=earnapp", headers=headers, timeout=12).json()
            if not isinstance(res_devs, list): res_devs = []
                
            payload_uuids = {"devices": [{"uuid": d['uuid']} for d in res_devs if isinstance(d, dict) and 'uuid' in d]}
            res_status = {}
            if payload_uuids["devices"]:
                res_st_req = requests.post("https://earnapp.com/dashboard/api/device_statuses?appid=earnapp&version=1.668.241", headers=headers, json=payload_uuids, timeout=12)
                if res_st_req.status_code == 200: res_status = res_st_req.json()
            
            devices_info = []
            acc_uptime_ms = 0
            
            for d in res_devs:
                if not isinstance(d, dict): continue
                uuid = d.get('uuid')
                
                raw_st = res_status.get(uuid, 'offline') if isinstance(res_status, dict) else 'offline'
                if isinstance(raw_st, list) and len(raw_st) > 0: raw_st = raw_st[0]
                
                if isinstance(raw_st, dict):
                    st_str = str(raw_st.get('status', 'offline')).lower()
                    if "banned" in st_str or "blocked" in st_str: st = "banned"
                    elif "online" in st_str or str(raw_st.get('status', '')).isdigit(): st = "online"
                    else: st = "offline"
                elif isinstance(raw_st, (int, float)) and raw_st > 0: st = "online"
                elif isinstance(raw_st, str):
                    st_lower = raw_st.lower()
                    if st_lower.isdigit() or st_lower == 'online': st = "online"
                    elif "banned" in st_lower or "blocked" in st_lower: st = "banned"
                    else: st = "offline"
                else: st = "online" if uuid in res_status else "offline"

                error_reason = str(d.get('error_reason', ''))
                if error_reason and ("blocked" in error_reason.lower() or "banned" in error_reason.lower() or "ip blocked" in error_reason.lower()):
                    st = "banned"

                raw_ips = d.get('ips', d.get('ip', []))
                if isinstance(raw_ips, list): clean_ips = [str(ip).strip() for ip in raw_ips if str(ip).strip()]
                else: clean_ips = [ip.strip().strip("'\"") for ip in str(raw_ips).split(',') if ip.strip()]

                uptime_raw = int(d.get('uptime', d.get('online_time', 0)) or 0)
                tot_uptime_raw = int(d.get('total_uptime', d.get('total_online_time', 0)) or 0)
                acc_uptime_ms += uptime_raw

                devices_info.append({
                    "name": str(d.get('title', d.get('name', 'Unknown'))),
                    "earned": float(d.get('earned', d.get('amount', 0)) or 0),
                    "earned_total": float(d.get('earned_total', d.get('total_earned', 0)) or 0),
                    "uptime": format_waktu(uptime_raw),
                    "total_uptime": format_waktu(tot_uptime_raw),
                    "uptime_raw": uptime_raw,
                    "country": str(d.get('country', 'UN')).upper(),
                    "status": st,
                    "error_reason": error_reason,
                    "ips": clean_ips
                })

            devices_info.sort(key=lambda x: natural_key(x['name']))

            chart_global = {"labels": [], "values": []}
            chart_top = {"labels": [], "values": [], "date": "-"}
            
            try:
                res_usage = requests.get("https://earnapp.com/dashboard/api/usage?appid=earnapp&step=daily", headers=headers, timeout=12)
                if res_usage.status_code == 200:
                    usage_data = res_usage.json()
                    if isinstance(usage_data, list) and len(usage_data) > 0:
                        agregasi_harian = {}
                        all_dates = set()
                        for p in usage_data:
                            if isinstance(p, dict) and "data" in p:
                                for tgl, durasi in p.get("data", {}).items():
                                    all_dates.add(tgl)
                                    val = int(durasi) if durasi is not None else 0
                                    agregasi_harian[tgl] = agregasi_harian.get(tgl, 0) + val
                        
                        if agregasi_harian:
                            tgl_tersortir = sorted(agregasi_harian.keys())[-7:]
                            chart_global["labels"] = [t[5:] for t in tgl_tersortir]
                            chart_global["values"] = [round(agregasi_harian[t] / 86400000, 2) for t in tgl_tersortir]
                        
                        if all_dates:
                            latest_date = sorted(list(all_dates))[-1]
                            chart_top["date"] = latest_date
                            node_daily = []
                            for p in usage_data:
                                if isinstance(p, dict):
                                    nm = str(p.get("title", p.get("name", "Unknown")))
                                    raw_pakai = p.get("data", {}).get(latest_date, 0) if isinstance(p.get("data"), dict) else 0
                                    pakai = int(raw_pakai) if raw_pakai is not None else 0
                                    node_daily.append((nm, pakai))
                            node_daily.sort(key=lambda x: x[1], reverse=True)
                            top_10 = node_daily[:10]
                            chart_top["labels"] = [n[0][:12] for n in top_10]
                            chart_top["values"] = [round(n[1] / 3600000, 1) for n in top_10]
            except Exception: pass

            active_count = sum(1 for x in devices_info if x['status'] == 'online')
            banned_count = sum(1 for x in devices_info if x['status'] == 'banned')
            total_count = len(devices_info)

            dashboard_data["total_online"] += active_count
            dashboard_data["total_nodes"] += total_count

            dashboard_data["accounts"].append({
                "id": acc_id,
                "name": name,
                "balance": balance,
                "lifetime": lifetime,
                "total_usage": format_waktu(acc_uptime_ms),
                "devices": devices_info,
                "active_nodes": active_count,
                "banned_nodes": banned_count,
                "total_nodes": total_count,
                "chart_global": chart_global,
                "chart_top": chart_top,
                "chart_history": chart_history
            })
        except Exception as e:
            dashboard_data["accounts"].append({"id": acc_id, "name": name, "error": str(e)})

    return jsonify(dashboard_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

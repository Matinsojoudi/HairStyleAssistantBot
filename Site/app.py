from flask import Flask, request, jsonify, send_file, Response, render_template, render_template_string, abort
import threading
import sqlite3
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import json
import io
import os

app = Flask(__name__)

# تنظیمات barbershop
SECRET_TOKEN = "CHANGE_ME_TOKEN"
BARBERSHOP_DB_PATH = "CHANGE_ME.db"

@app.route('/api/new_reservation', methods=["POST"])
def receive_new_reservation():
    token = request.headers.get("Authorization")
    if not token or token != ";suirw[gjvno;hwiw[ue99348tylulig;]]":
        return jsonify({"status": "error", "message": "Invalid token"}), 403

    try:
        data = request.get_json(force=True) or {}
        db_path = data.get("database_name")
        reservation = data.get("reservation")

        if not db_path or not reservation:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO reservations (user_id, staff_id, services, day, time_slot, total_price, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)
            ''', (
                reservation["user_id"],
                reservation["staff_id"],
                ','.join(map(str, reservation["services"])),
                reservation["day"],
                reservation["time_slot"],
                reservation["total_price"],
                reservation["created_at"],
            ))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/api/sync_full_data', methods=["POST"])
def sync_full_data():
    token = request.headers.get("Authorization")
    if token != ";suirw[gjvno;hwiw[ue99348tylulig;]]":
        return jsonify({"status": "error", "message": "Invalid token"}), 403

    try:
        data = request.get_json(force=True) or {}
        db_path = data.get("database_name")
        tables = data.get("tables")

        if not db_path or not tables:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            # حذف رکوردهای قبلی (اختیاری، اگر می‌خواهی replace کنی)
            for tname in tables.keys():
                c.execute(f"DELETE FROM {tname}")
            # درج رکورد جدید
            for tname, rows in tables.items():
                if not rows:
                    continue
                columns = rows[0].keys()
                qmarks = ",".join(["?"] * len(columns))
                for row in rows:
                    values = [row[col] for col in columns]
                    c.execute(
                        f"INSERT INTO {tname} ({','.join(columns)}) VALUES ({qmarks})", values
                    )
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/barbershop_data', methods=['GET'])
def get_all_data():
    token = request.headers.get('Authorization')
    if token != SECRET_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db_path = request.args.get("database", BARBERSHOP_DB_PATH)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        def fetch_table(table):
            try:
                c.execute(f"SELECT * FROM {table}")
                cols = [col[0] for col in c.description]
                return [dict(zip(cols, row)) for row in c.fetchall()]
            except sqlite3.OperationalError:
                return []

        data = {
            "reservations": fetch_table("reservations"),
            "users": fetch_table("users"),
            "user_info": fetch_table("user_info"),
            "staff": fetch_table("staff"),
            "services": fetch_table("services"),
        }
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

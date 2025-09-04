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

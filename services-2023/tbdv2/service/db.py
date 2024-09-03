import sqlite3, os, threading
from datetime import datetime

def connect():
	return sqlite3.connect(os.environ.get("DB", "/tmp/db.sqlite"))

def init():
	with connect() as conn:
		conn.execute("""
			CREATE TABLE IF NOT EXISTS instance (
				id text PRIMARY KEY,
				secret text NOT NULL,
				code text NOT NULL,
				description text NOT NULL,
				config text NOT NULL,
				created text NOT NULL,
				executed text DEFAULT NULL,
				stdout text DEFAULT NULL,
				stderr text DEFAULT NULL,
				stats text DEFAULT NULL
			);
		""")

		count, = conn.execute("SELECT count(*) FROM instance").fetchone()
		print(f"[{datetime.now()}] Db: Opened database with {count} instances", flush=True)
	cleanup()

cleanup_timer = None

def cleanup():
	import wasm
	global cleanup_timer

	memory_instances = list(wasm.instances.keys())

	with connect() as conn:
		threshold = int(os.environ.get("CLEANUP_THRESHOLD", 300))
		total, = conn.execute("SELECT COUNT(*) FROM instance").fetchone()
		count = conn.execute("""
			DELETE FROM instance
			WHERE executed < datetime('now', '-' || ? || ' seconds')
				OR (executed IS NULL AND created < datetime('now', '-' || ? || ' seconds'))
		""", [ threshold, threshold ]).rowcount
		new = { id for id, in conn.execute("SELECT id FROM instance").fetchall() }

	for id in memory_instances:
		if id not in new:
			del wasm.instances[id]

	if count > 0:
		print(f"[{datetime.now()}] Db: Cleanup deleted {count}/{total} instances, {len(wasm.instances)} currently active", flush=True)

	cleanup_timer = threading.Timer(int(os.environ.get("CLEANUP_INTERVAL", 60)), cleanup)
	cleanup_timer.start()

def stop():
	global cleanup_timer

	if cleanup_timer is not None:
		cleanup_timer.cancel()
		cleanup_timer = None

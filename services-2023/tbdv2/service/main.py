import flask, uuid, secrets, requests, functools, json, traceback, os

import wasm, db

app = flask.Flask(__name__)
app.json.compact = False # type: ignore

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

EXAMPLE_CODE = """
import sys, time
print("Hello from", sys.platform, "id", instance.id, "at", time.time())
print("Hey mom, I can see my own code:", instance.code)
print("And here is my config input:", instance.config)
"""

def authenticate(allow_localhost=False):
	def inner(endpoint):
		@functools.wraps(endpoint)
		def wrapped(*args, **kwargs):
			id = str(uuid.UUID(flask.request.view_args.get("id"))) if flask.request.view_args is not None else None
			secret = flask.request.args.get("secret")

			with db.connect() as conn:
				instance_secret, = conn.execute("SELECT secret FROM instance WHERE id = ?", [ id ]).fetchone()

			authenticated = secret == instance_secret or (allow_localhost and flask.request.remote_addr == "127.0.0.1")
			return endpoint(authenticated, *args, **kwargs)
		return wrapped
	return inner

def print_errors(endpoint):
	@functools.wraps(endpoint)
	def wrapped(*args, **kwargs):
		try:
			return endpoint(*args, **kwargs)
		except:
			return flask.render_template("error.html", error=traceback.format_exc())
	return wrapped

@app.route("/static/<path:path>")
def send_report(path):
	return flask.send_from_directory("static", path)

@app.get("/")
def index():
	return flask.render_template("index.html", id=uuid.uuid4(), example_code=EXAMPLE_CODE)

@app.post("/")
@print_errors
def new():
	id = str(uuid.UUID(flask.request.form.get("id")))
	code = str(flask.request.form["code"])
	description = str(flask.request.form.get("description", "")).replace("\r", "")
	config = str(flask.request.form.get("config", "")).replace("\r", "")
	secret = secrets.token_hex(32)

	if config.startswith("http://") or config.startswith("https://"):
		config = requests.get(config).text

	with db.connect() as conn:
		conn.execute("INSERT INTO instance (id, secret, code, description, config, created) VALUES (?, ?, ?, ?, ?, datetime('now'))",
			(id, secret, code, description, config))
	wasm.run(id)

	return flask.redirect(flask.url_for("detail", id=id, secret=secret))

@app.get("/api/<id>")
@print_errors
@authenticate(allow_localhost=True)
def api(authenticated: bool, id):
	id = str(uuid.UUID(id))
	clone_id = str(uuid.UUID(flask.request.args.get("clone_uuid"))) if "clone_uuid" in flask.request.args else None

	if clone_id is not None:
		with db.connect() as conn:
			conn.execute("INSERT INTO instance (id, secret, code, description, code, config, created) SELECT ?, ?, code, description, '', '', created FROM instance WHERE id = ?", [ clone_id, clone_id, id ])

		clone_log = flask.request.args.get("clone_log", f"Cloned from {id}!")
		clone_log = clone_log[1:] if clone_log[0] == "\n" else clone_log
		secret = secrets.token_hex(32)

		with db.connect() as conn:
			conn.execute("UPDATE instance SET description = ?, secret = ? WHERE id = ?", [ clone_log, secret, clone_id ])

		id = clone_id

	with db.connect() as conn:
		secret, description, created, executed = conn.execute("SELECT secret, description, created, executed FROM instance WHERE id = ?", [ id ]).fetchone()

	result = {
		"id": id,
		"secret": secret,
		"description": description,
		"created": created,
		"executed": executed,
	}

	if not authenticated and "FLAG" in description:
		result["description"] = "Ani piču"
	if not authenticated and clone_id is None:
		del result["secret"]

	return flask.jsonify(result)

@app.get("/<id>")
@print_errors
@authenticate(allow_localhost=False)
def detail(authenticated: bool, id):
	id = str(uuid.UUID(id))

	if not authenticated:
		return flask.abort(403)

	details = requests.get(f"http://127.0.0.1:{PORT}/api/{id}").json()
	instance = wasm.instances.get(id)

	with db.connect() as conn:
		stdout, stderr, stats = conn.execute("SELECT stdout, stderr, stats FROM instance WHERE id = ?", [ id ]).fetchone()

	return flask.render_template("detail.html", details=details, instance=instance, stdout=stdout, stderr=stderr, stats=json.dumps(json.loads(stats), indent=4))

@app.post("/<id>")
@print_errors
@authenticate(allow_localhost=False)
def rerun(authenticated: bool, id):
	id = str(uuid.UUID(id))
	secret = flask.request.args.get("secret")

	if not authenticated:
		return flask.abort(403)

	wasm.run(id)
	return flask.redirect(flask.url_for("detail", id=id, secret=secret))

if __name__ == "__main__":
	db.init()
	wasm.init()
	app.run(host=HOST, port=PORT)
	db.stop()

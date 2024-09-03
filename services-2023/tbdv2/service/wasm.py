from __future__ import annotations
from dataclasses import dataclass
import tempfile, os, pickle, json, io

import db

FUEL = int(os.environ.get("FUEL", 2_000_000_000))

def execute_code(code, stdin=None, fuel=FUEL):
	import wasmtime

	engine_cfg = wasmtime.Config()
	engine_cfg.consume_fuel = True
	engine_cfg.cache = True

	linker = wasmtime.Linker(wasmtime.Engine(engine_cfg))
	linker.define_wasi()

	python_module = wasmtime.Module.from_file(linker.engine, "wasm/python-3.11.1.wasm")

	config = wasmtime.WasiConfig()

	config.argv = ("python", "-B", "-c", code)
	config.preopen_dir(".", "/")
	config.env = [
		[ "PYTHONPATH", "/wasm/python311.zip" ],
	]

	with tempfile.TemporaryDirectory() as chroot:
		filename_stdout = os.path.join(chroot, "stdout")
		filename_stderr = os.path.join(chroot, "stderr")
		filename_stdin = os.path.join(chroot, "stdin")

		with open(filename_stdin, "wb") as f:
			pickle.dump(stdin, f)

		config.stdout_file = filename_stdout
		config.stderr_file = filename_stderr
		config.stdin_file = filename_stdin

		store = wasmtime.Store(linker.engine)

		store.add_fuel(fuel)
		store.set_wasi(config)
		instance = linker.instantiate(store, python_module)

		start = instance.exports(store)["_start"]
		mem = instance.exports(store)["memory"]

		try:
			start(store) # type: ignore
		except Exception:
			pass

		with open(filename_stdout) as f:
			output_stdout = f.read()
		with open(filename_stderr) as f:
			output_stderr = ""
			for line in f:
				if not line.startswith("Could not find platform"):
					output_stderr += line + "\n"

		return {
			"output": {
				"stdout": output_stdout,
				"stderr": output_stderr,
			},
			"stats": {
				"mem_size": mem.size(store), # type: ignore
				"data_len": mem.data_len(store), # type: ignore
				"fuel_used": store.fuel_consumed(),
				"fuel_max": fuel,
			}
		}

@dataclass(init=False, repr=True, slots=True)
class Instance:
	id: str
	code: str
	config: str

	def __init__(self, id: str, code: str | None = None, config: str | None = None):
		if type(id) is not str:
			return

		self.id = id
		import db
		with db.connect() as conn:
			if code is not None:
				self.code = code
			else:
				self.code = conn.execute("SELECT code FROM instance WHERE id = ?", [ id ]).fetchone()[0]

			if config is not None:
				self.config = config
			else:
				config = str(conn.execute("SELECT config FROM instance WHERE id = ?", [ id ]).fetchone()[0])

				try:
					self.config = RestrictedUnpickler.loads(config)
				except:
					self.config = config

class RestrictedUnpickler(pickle.Unpickler):
	def find_class(self, module, name):
		if module == "wasm" and name == "Instance":
			return Instance
		raise pickle.UnpicklingError(f"'{module}.{name}' is forbidden")

	@staticmethod
	def loads(data: str):
		return RestrictedUnpickler.loadst(io.BytesIO(data.encode("utf-8")))

	@staticmethod
	def loadst(data):
		return RestrictedUnpickler(data).load()

instances = {}

def init():
	global instances
	with db.connect() as conn:
		for id, code, config in conn.execute("SELECT id, code, config FROM instance").fetchall():
			instances[id] = Instance(id, code, config)

def run(id: str):
	global instances
	instance = instances[id] = Instance(id)
	init_code = f"import pickle, sys, wasm; instances = wasm.RestrictedUnpickler.loadst(sys.stdin.buffer); instance = instances.get('{id}');"
	result = execute_code(init_code + instance.code, instances)

	with db.connect() as conn:
		conn.execute("UPDATE instance SET executed = datetime('now'), stdout = ?, stderr = ?, stats = ? WHERE id = ?",
			[ result["output"]["stdout"], result["output"]["stderr"], json.dumps(result["stats"]), id ])

import os, requests, uuid, json, pickle, secrets, logging
from bs4 import BeautifulSoup
from typing import Tuple, Union

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

PORT = int(os.environ.get("PORT", 5000))

class CheckerCommon(checkerlib.BaseChecker):
	def __init__(self, ip: str, team: int):
		super().__init__(ip, team)
		self.port = PORT
		self.url = f"http://{self.ip}:{self.port}"

	def create_instance(self, data: dict) -> BeautifulSoup:
		detail = requests.post(self.url, data=data).text
		return BeautifulSoup(detail, "html.parser")

	def rerun_instance(self, id: str, secret: str) -> BeautifulSoup:
		detail = requests.post(f"{self.url}/{id}?secret={secret}").text
		return BeautifulSoup(detail, "html.parser")

	def clone_instance(self, id: str, clone_uuid: str, clone_log: str) -> dict:
		return requests.get(f"{self.url}/api/{id}?clone_uuid={clone_uuid}&clone_log={clone_log}").json()

	def error(self, status: CheckResult, msg: str, debug: str = "") -> Tuple[CheckResult, str]:
		logging.warning(f"{msg} ({debug})" if debug != "" else msg)
		return status, msg

	def extract_field(self, soup: BeautifulSoup, id: str) -> Union[str, None]:
		field = soup.find(id=id)
		return None if field is None else field.get_text().strip()

	def check_service(self):
		id = str(uuid.uuid4())
		rnd = secrets.token_hex(32)

		# Create instance with random description and config
		detail = self.create_instance({
			"id": id,
			"description": rnd,
			"code": f"print(instance.config['rnd'])",
			"config": pickle.dumps({ "rnd": rnd }, 0),
		})

		# Check if description is set correctly and code was executed
		description = self.extract_field(detail, "f_description")
		config = self.extract_field(detail, "f_config")
		stdout = self.extract_field(detail, "f_stdout")
		secret = self.extract_field(detail, "f_secret")
		created = self.extract_field(detail, "f_created")

		if description != rnd:
			return self.error(CheckResult.FAULTY, "Received incorrect description field", f"got {description!r} expected {rnd!r}")
		if config != str({ "rnd": rnd }):
			return self.error(CheckResult.FAULTY, "Received incorrect config field", f"got {config!r} expected {str({ 'rnd': rnd })!r}")
		if stdout != rnd:
			return self.error(CheckResult.FAULTY, "Received incorrect code stdout", f"got {stdout!r} expected {rnd!r}")
		if secret == "":
			return self.error(CheckResult.FAULTY, "Received empty secret")

		# Now create second instance, to check if url fetching and secrets work
		detail = self.create_instance({
			"id": uuid.uuid4(),
			"code": "print('YEET')",
			"config": f"http://127.0.0.1:{PORT}/api/{id}?secret={secret}",
		})

		# Check if config field contains correct API response
		try:
			config = json.loads(detail.find_all(id="f_config")[0].get_text())
			del config["created"]
			del config["executed"]

			expected = { "id": id, "secret": secret, "description": rnd }
			if config != expected:
				return self.error(CheckResult.FAULTY, "Received incorrect content from api", f"got {config!r} expected {expected!r}")
		except BaseException as error:
			return self.error(CheckResult.FAULTY, "Received incorrect content from api", str(error))

		# Now check if api cloning works
		detail = self.clone_instance(id, str(uuid.uuid4()), rnd)
		if detail.get("description") != rnd:
			return self.error(CheckResult.FAULTY, "Received incorrect description from api after clone", f"got {detail.get('description')!r} expected {rnd!r}")
		if detail.get("created") != created:
			return self.error(CheckResult.FAULTY, "Received incorrect created date from api after clone", f"got {detail.get('created')!r} expected {created!r}")

		# All is well
		return CheckResult.OK, "Ok"

class CheckerFlagstore1(CheckerCommon):
	def place_flag(self, tick):
		id = str(uuid.uuid4())
		flag = checkerlib.get_flag(tick)

		# Create flag instance
		detail = self.create_instance({
			"id": id,
			"description": f"FLAG:{flag}",
			"code": f"print('YEET')",
		})

		# Set state
		checkerlib.set_flagid(id)
		checkerlib.store_state(f"instance_secret_{tick}", self.extract_field(detail, "f_secret"))

		# All is well
		return CheckResult.OK, "Ok"

	def check_flag(self, tick):
		id = checkerlib.get_flagid(tick)
		flag = checkerlib.get_flag(tick)
		secret = checkerlib.load_state(f"instance_secret_{tick}")

		# Check if we have id and secret
		if id is None or secret is None:
			return self.error(CheckResult.FLAG_NOT_FOUND, "Missing flag id or secret from past tick", f"{id=!r}, {secret=!r}")

		# Rerun instance
		detail = self.rerun_instance(id, secret)

		# Check if flag is present
		description = self.extract_field(detail, "f_description")
		if description is None:
			return self.error(CheckResult.FLAG_NOT_FOUND, "Received no flag in description field", f"got {description!r} expected {'FLAG:'+flag!r}")
		if description != f"FLAG:{flag}":
			return self.error(CheckResult.FLAG_NOT_FOUND, "Received incorrect flag in description field", f"got {description!r} expected {'FLAG:'+flag!r}")

		# All is well
		return checkerlib.CheckResult.OK, "Ok"

class CheckerFlagstore2(CheckerCommon):
	def place_flag(self, tick):
		id = str(uuid.uuid4())
		flag = checkerlib.get_flag(tick)

		# Create flag instance
		detail = self.create_instance({
			"id": id,
			"code": "print(instance.config['flag'])",
			"config": pickle.dumps({ "flag": flag }, 0),
		})

		# Set state
		checkerlib.set_flagid(id)
		checkerlib.store_state(f"instance_secret_{tick}", self.extract_field(detail, "f_secret"))

		# All is well
		return CheckResult.OK, "Ok"

	def check_flag(self, tick):
		id = checkerlib.get_flagid(tick)
		flag = checkerlib.get_flag(tick)
		secret = checkerlib.load_state(f"instance_secret_{tick}")

		# Check if we have id and secret
		if id is None or secret is None:
			return self.error(CheckResult.FLAG_NOT_FOUND, "Missing flag id or secret from past tick", f"{id=!r}, {secret=!r}")

		# Rerun instance
		detail = self.rerun_instance(id, secret)

		# Check if flag is present
		stdout = self.extract_field(detail, "f_stdout")
		if stdout is None:
			return self.error(CheckResult.FLAG_NOT_FOUND, "Received no flag in stdout field", f"got {stdout!r} expected {flag!r}")
		if stdout != flag:
			return self.error(CheckResult.FLAG_NOT_FOUND, "Received incorrect flag in stdout field", f"got {stdout!r} expected {flag!r}")

		# All is well
		return checkerlib.CheckResult.OK, "Ok"

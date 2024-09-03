import os, requests, json, secrets, random, logging, base64
from pwn import *

from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

PORT = int(os.environ.get("PORT", 4567))

logging.basicConfig(level=logging.info)

class FaultException(Exception):
    pass

def generateRandomString() -> str:
    return secrets.token_urlsafe(random.randint(10, 30))

class ProgCodexApiClient():
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()

        if not len(self.session.get(self.url).text):
            raise Exception("Service down")
    
    def login(self, username: str, password: str) -> bool:
        data = {"username": username, "password": password}
        logging.info(f"Logging in user {username}:{password}")
        response = self.session.post(f"{self.url}/login", json=data)
        if response.status_code == 202:
            return True
        raise FaultException("Login failed")

    def signup(self, username: str, password: str):
        data = {"username": username, "password": password}
        logging.info(f"Signing up user {username}:{password}")
        response = self.session.post(f"{self.url}/signup", json=data)
        if response.status_code == 201:
            return response.json()
        raise FaultException("Signup failed")

    def logout(self) -> bool:
        logging.info(f"Logging out")
        response = self.session.delete(f"{self.url}/logout")
        if response.status_code == 204:
            return True
        raise FaultException("Logout failed")

    def me(self) -> dict:
        logging.info(f"Requesting me")
        response = self.session.get(f"{self.url}/me")
        if response.status_code == 200:
            return response.json()
        raise FaultException("Me failed")
    
    def submissions(self) -> list:
        logging.info(f"Getting submissions")
        response = self.session.get(f"{self.url}/submissions")
        if response.status_code == 200:
            return response.json()
        raise FaultException("Submissions failed")

    def addsubmission(self, name: str, payload: str):
        data = {"name": name, "payload": payload}
        logging.info(f"Adding submission {name}:{payload}")
        response = self.session.post(f"{self.url}/submissions", json=data)
        if response.status_code == 201:
            return response.json()['id']
        raise FaultException("Add submission failed")

    def getsubmission(self, submission_id: str, sharetoken="") -> dict:
        if sharetoken != "":
            logging.info(f"Getting submission with sharetoken {sharetoken}")
            response = self.session.get(f"{self.url}/submissions/{submission_id}?sharetoken={sharetoken}")
        else:
            logging.info(f"Getting submission {submission_id}")
            response = self.session.get(f"{self.url}/submissions/{submission_id}")
        if response.status_code == 200:
            return response.json()
        raise FaultException("Get submission failed")

    def getsubmissionstats(self, filter: str) -> dict:
        logging.info(f"Getting submission stats with filter {filter}")
        response = self.session.get(f"{self.url}/submissions/stats?query={filter}")
        if response.status_code == 200:
            return response.json()
        raise FaultException("Get submission stats failed")

    def sharesubmission(self, submission_id: str, sharedwith: list):
        data = {"sharedwith": sharedwith}
        logging.info(f"Sharing submission {submission_id} with {sharedwith}")
        response = self.session.put(f"{self.url}/submissions/{submission_id}", json=data)
        if response.status_code == 200:
            return response.json()
        raise FaultException("Share submission failed")

    def executesubmission(self, submission_id: str):
        logging.info(f"Executing submission {submission_id}")
        response = self.session.patch(f"{self.url}/submissions/{submission_id}?inputid=0")
        if response.status_code == 200:
            return response.json()
        raise FaultException("Execute submission failed")

    def addcomment(self, submission_id: str, comment: str):
        data = {"comment": comment}
        logging.info(f"Adding comment {comment} to submission {submission_id}")
        response = self.session.post(f"{self.url}/submissions/{submission_id}/comments", json=data)
        if response.status_code == 200:
            return response.json()
        raise FaultException("Add comment failed")

class ProgCodexClientSimulator(ProgCodexApiClient):
    def __init__(self, url: str):
        super().__init__(url+"/api")
        self.username = generateRandomString()[:25]
        self.password = generateRandomString()

        self.uuid = self.signup(self.username, self.password)["id"]
        self.login(self.username, self.password)

    def checkMainPage(self):
        rawurl = self.url.split("/api")[0]
        # check javascript
        logging.info(f"Checking main page javascript")
        response = self.session.get(f"{rawurl}/script.js")
        if response.status_code != 200 or response.text == "":
            raise FaultException("Main page javascript not loading")

        # check main page
        logging.info(f"Checking main page")
        response = self.session.get(f"{rawurl}/")
        if response.status_code != 200 or response.text == "":
            raise FaultException("Main page javascript not loading")

    def createSubmissionAndCheckExecution(self) -> str:
        submission_type = random.randint(0,1)
        if submission_type == 0:
            # choose random file from onlyprinting/generated directory and read it
            logging.info(f"Creating submission of type onlyprinting")
            filename = random.choice(os.listdir('shellcodes/onlyprinting/generated'))
            submission_payload = open(f"shellcodes/onlyprinting/generated/{filename}", "rb").read()
        else:
            logging.info(f"Creating submission of type readingfile")
            filename = random.choice(os.listdir('shellcodes/readingfile/generated'))
            submission_payload = open(f"shellcodes/readingfile/generated/{filename}", "rb").read()

        uuid = self.addsubmission(generateRandomString(), base64.b64encode(submission_payload).decode())

        execution_result = self.executesubmission(uuid)["output"]

        if submission_type == 0:
            if execution_result != filename:
                raise FaultException("Unexpected execution result")
        else:
            # open file and get first n characters as string
            with open(f"./graph.txt", "rb") as f:
                expected_result = f.read(int(filename))
            if execution_result != expected_result.decode():
                raise FaultException("Unexpected execution result")

        return uuid

class CheckerCommon(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.port = PORT
        self.url = f"http://{self.ip}:{self.port}"

    def check_service(self):
        try:
            # first client
            c1 = ProgCodexClientSimulator(self.url)
        except FaultException as error:
            return CheckResult.FAULTY, error
        except BaseException as error:
            return CheckResult.DOWN, error

        try:
            # check if page loads and create submission
            c1.checkMainPage()
            uuid = c1.createSubmissionAndCheckExecution()

            sharetoken = c1.getsubmission(uuid)["submission"]["sharetoken"]

            # second client
            c2 = ProgCodexClientSimulator(self.url)
            c2.checkMainPage()

            if c2.me()["username"] != c2.username:
                raise FaultException("Getting me failed")

            # try getting the submision first with sharetoken then with sharedwith
            c2.getsubmission(uuid, sharetoken)

            # test submissions endpoint
            c1subs = c1.submissions()
            c2subs = c2.submissions()

            if c1subs["mine"][0]["_id"] != uuid or len(c2subs["mine"]) != 0 or len(c2subs["sharedwithme"]) != 0:
                raise FaultException("Failed to get submission")

            c1.sharesubmission(uuid, [c2.username])

            c2subs = c2.submissions()

            if "sharedwithme" not in c2subs or c2subs["sharedwithme"][0]["_id"] != uuid:
                raise FaultException("Failed to share submission")

            sharedsub = c2.getsubmission(uuid)

            if not (sharedsub["submission"]["sharedwith"][0]["username"] == c2.username and sharedsub["submission"]["sharedwith"][0]["id"] == c2.uuid):
                raise FaultException("Failed to share submission")

            comment = generateRandomString()
            c2.addcomment(uuid, comment)

            stats = c1.getsubmissionstats("{}")
            if not "statistics" in stats:
                raise FaultException("Failed to get submission stats")

            for i in stats["statistics"]:
                if i["author"] == c1.username:
                    if i["count"] != 1:
                        raise FaultException("Failed to checking submission stats")

            stats = c1.getsubmissionstats(json.dumps({"author": c1.username}))
            if not "statistics" in stats or len(stats["statistics"]) != 1:
                raise FaultException("Failed to get submission stats")

            for i in stats["statistics"]:
                if i["author"] == c1.username:
                    if i["count"] != 1:
                        raise FaultException("Failed to checking submission stats")

            if not c1.getsubmission(uuid)["submission"]["comments"][0]["comment"] == comment:
                raise FaultException("Failed to get comment")

            c1.logout()
            c2.logout()

        except BaseException as error:
            return CheckResult.FAULTY, error
        return CheckResult.OK, "OK"

class CheckerFlagstore1(CheckerCommon):
    def place_flag(self, tick):
        flag = checkerlib.get_flag(tick)
        context.arch='amd64'
        payload = base64.b64encode(asm(shellcraft.amd64.linux.echo(flag))).decode()

        try:
            c1 = ProgCodexClientSimulator(self.url)

            uuid = c1.addsubmission(generateRandomString(), payload)
        except FaultException as error:
            return CheckResult.FAULTY, error

        checkerlib.set_flagid(json.dumps({"username":c1.username, "id":uuid}))
        checkerlib.store_state(f"store1_logindetails_{tick}", json.dumps({"username":c1.username, "password":c1.password}))

        return CheckResult.OK, "OK"

    def check_flag(self, tick):
        try:
            flag = checkerlib.get_flag(tick)
            flagid = json.loads(checkerlib.get_flagid(tick))["id"]
            details = json.loads(checkerlib.load_state(f"store1_logindetails_{tick}"))
        except BaseException as error:
            return CheckResult.FLAG_NOT_FOUND, "flag was not planted"

        try:
            c1 = ProgCodexApiClient(self.url+"/api")
        except FaultException as error:
            return CheckResult.FAULTY, error
        except BaseException as error:
            return CheckResult.DOWN, error

        try:
            c1.login(details["username"], details["password"])

            if not flag in c1.executesubmission(flagid)["output"]:
                raise FaultException("Failed to get flag")
        except BaseException as error:
            return CheckResult.FLAG_NOT_FOUND, error
        return CheckResult.OK, "OK"

class CheckerFlagstore2(CheckerCommon):
    def place_flag(self, tick):
        flag = checkerlib.get_flag(tick)
        context.arch='amd64'
        payload = base64.b64encode(asm(shellcraft.amd64.linux.echo(generateRandomString()))).decode()

        try:
            c1 = ProgCodexClientSimulator(self.url)

            uuid = c1.addsubmission(generateRandomString(), payload)
            c1.addcomment(uuid, flag)
        except FaultException as error:
            return CheckResult.FAULTY, error

        checkerlib.set_flagid(json.dumps({"username":c1.username, "id":uuid}))
        checkerlib.store_state(f"store2_logindetails_{tick}", json.dumps({"username":c1.username, "password":c1.password}))

        return CheckResult.OK, "OK"

    def check_flag(self, tick):
        try:
            flag = checkerlib.get_flag(tick)
            flagid = json.loads(checkerlib.get_flagid(tick))["id"]
            details = json.loads(checkerlib.load_state(f"store2_logindetails_{tick}"))
        except BaseException as error:
            return CheckResult.FLAG_NOT_FOUND, "flag was not planted"

        try:
            c1 = ProgCodexApiClient(self.url+"/api")
        except FaultException as error:
            return CheckResult.FAULTY, error
        except BaseException as error:
            return CheckResult.DOWN, error

        try:
            c1.login(details["username"], details["password"])

            if not flag == c1.getsubmission(flagid)["submission"]["comments"][0]["comment"]:
                raise FaultException("Failed to get flag")
        except BaseException as error:
            return CheckResult.FLAG_NOT_FOUND, error
        return CheckResult.OK, "OK"

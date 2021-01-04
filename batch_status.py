import requests
import json

with open('config_dev.json') as file:
    CONFIG = json.load(file)

api_url = CONFIG['api_url']
api_key = CONFIG['api_key']
api_secret = CONFIG['api_secret']
HTTP_SESSION = requests.Session()
HTTP_SESSION.auth = (api_key, api_secret)

batch = input("Enter batch number:")

r = HTTP_SESSION.get(api_url+'/v2/Imports/' + str(batch))
print(r.text)

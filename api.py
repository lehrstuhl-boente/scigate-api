# function called by the API
import json

def search(**kwargs):
	jsonInput=json.loads(list(kwargs.values())[0].decode('utf-8'))
	print(jsonInput)
	return json.dumps({})
	
def load(**kwargs):
	jsonInput=json.loads(list(kwargs.values())[0].decode('utf-8'))
	print(jsonInput)
	return json.dumps({})
	
def queryStatus(**kwargs):
	jsonInput=json.loads(list(kwargs.values())[0].decode('utf-8'))
	print(jsonInput)
	return json.dumps({})



# function called by the API
import json

def search(**kwargs):
	jsonInput=list(kwargs.values())[0]
	print(jsonInput)
	return json.dumps({})
	
def load(**kwargs):
	jsonInput=list(kwargs.values())[0]
	print(jsonInput)
	return json.dumps({})
	
def queryStatus(**kwargs):
	jsonInput=list(kwargs.values())[0]
	print(jsonInput)
	return json.dumps({})



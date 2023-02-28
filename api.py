# function called by the API
import json

def search(**kwargs):
	jsonBody=list(kwargs.values())[0]
	print(jsonBody)
	return jsonBody
	
def load(**kwargs):
	jsonBody=list(kwargs.values())[0]
	return jsonBody
	
def queryStatus(**kwargs):
	jsonBody=list(kwargs.values())[0]
	return jsonBody



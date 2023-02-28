# function called by the API
import json
import requests

APIURL="http://v2202109132150164038.luckysrv.de:8080/"

def search(sdata):
	reply={}
	reply['status']='ok'
	try:
		collection=sdata['collection']
		if collection in ['entscheidsuche','boris','zora','swisscovery']:
			query=sdata['query']
			maxHits=100
			if 'maxHits' in sdata:
				maxHits=sdata['maxHits']
			maxReply=100
			if 'maxReply' in sdata:
				maxReply=sdata['maxReply']
			result={}
			data={'engine': collection, 'type': 'search', 'term': query}
			r=requests.post(url=APIURL,json=data)
			reply['ergebnis']=r.text 				
		else:
			reply['status']='error'
			reply['error']="Collection '"+collection+"' unknown"	
	except:
		reply['status']='error'
	return reply
	
def load(sdata):
	reply={}
	reply['status']='ok'
	return reply
	
def queryStatus(sdata):
	reply={}
	reply['status']='ok'
	return reply



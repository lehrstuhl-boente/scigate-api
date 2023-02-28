# function called by the API
import json
import requests
import time
import os
import csv

APIURL="http://v2202109132150164038.luckysrv.de:8080/"
CHUNK=100
PARENTDIR="/home/jorn/scigateapi/data"

def search(sdata):
	reply={}
	reply['status']='ok'
	id=millisec = int(time.time() * 1000)

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
			ergebnis=r.text
			result=json.loads(ergebnis)
			if result['status']=='ok':
				hits=result['hits']
				reply['hits']=hits
				if hits>maxHits:
					hits=maxHits
					reply['hitsTruncated']=True
				if hits>maxReply:
					reply['token']=id
				else:
					reply=getData(query,collection,hits,id)
			else:
				return result	
		else:
			reply['status']='error'
			reply['error']="Collection '"+collection+"' unknown"	
	except:
		reply['status']='error'
	return reply
	
def getData(query,collection,hits,id):
	start=0
	hitlist=[]
	verzeichnisname=request"+str(id)
	dir=PARENTDIR+"/"+verzeichnisname
	os.mkdir(dir)
	try:
		while start<hits:
			count=CHUNK
			if start+count>hits:
				count=hits-start
			data={'engine': collection, 'type': 'hitlist', 'term': query, 'start':start, 'count': count}
			r=requests.post(url=APIURL,json=data)
			ergebnis=r.text
			result=json.loads(ergebnis)
			if result['status']=='ok':
				hitlist.extend([[i['description'][0], i['description'][1], i['url'], i['url'].after('https://entscheidsuche.ch/view/')] for i in result['hitlist']])
			else:
				return result
			start+=count
		with open(dir+"/hitlist.csv", 'w') as f:
			write = csv.writer(f)
			write.writerow(["Description1","Description2","URL","ID"])
			write.writerows(hitlist)
		reply['verzeichnis']=verzeichnisname
			
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



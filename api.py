# function called by the API
import json
import requests
import time
import datetime
import os
import csv
import random

APIURL="http://v2202109132150164038.luckysrv.de:8080/"
MYAPIURL="http://v2202109132150164038.luckysrv.de:5001/api/"
CHUNK=100
PARENTDIR="/home/jorn/scigateapi/data"
PREDIR="request"
MAXREPLY=200

def search(sdata):
	reply={}
	reply['status']='ok'
	# add some random to the id so that guessing it becomes difficult
	id=millisec = int(time.time() * 100000000000)+randint(0,100000000)

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
				if maxReply > MAXREPLY:
					maxReply=MAXREPLY
					reply["warning"]="Synchronous requests are limited to "+str(MAXREPLY)+" hits"
			result={}
			data={'engine': collection, 'type': 'search', 'term': query}
			r=requests.post(url=APIURL,json=data)
			ergebnis=r.text
			result=json.loads(ergebnis)
			if result['status']=='ok':
				hits=result['hits']
				reply['hits']=hits
				reply['token']=str(id)
				reply['check']=MYAPIURL+'status?{"id":'+str(id)+'}'
				reply['load']=MYAPIURL+'load?{"id":'+str(id)+'}'
				if hits>maxHits:
					hits=maxHits
					reply['hitsTruncated']=True
				if hits>maxReply:
					new_thread = Thread(target=getData,args=(query,collection,hits,id))
					new_thread.run()
				else:
					print("Rufe nun getData mit '"+query+"' auf.")
					reply.update(getData(query,collection,hits,id))
			else:
				result['errormodule']="search: return from search-command"
				return result	
		else:
			reply['status']='error'
			reply['errormodule']="search"
			reply['error']="Collection '"+collection+"' unknown"	
	except:
		reply['errormodule']="search"
		reply['error']="exception caught"	
		reply['status']='error'
	finally:
		return reply
	
def getData(query,collection,hits,id):
	status={ 'start': datetime.datetime.fromtimestamp(id/100000000000.0).isoformat(), 'last': datetime.datetime.fromtimestamp(time.time()).isoformat(), 'hits': hits, 'fetched': 0, 'status': 'running'}
	saveStatus(status, id)
	reply={}
	reply['status']='ok'
	start=0
	hitlist=[]
	verzeichnisname=PREDIR+str(id)
	dir=PARENTDIR+"/"+verzeichnisname
	print("lege nun Verzeichnis '"+dir+"' an.")
	os.mkdir(dir)
	try:
		while start<hits:
			print("Durchlauf hitlist-Schleife start mit "+str(start))
			count=CHUNK
			if start+count>hits:
				count=hits-start
			data={'engine': collection, 'type': 'hitlist', 'term': query, 'start':start, 'count': count}
			r=requests.post(url=APIURL,json=data)
			ergebnis=r.text
			#print("Ergebnis von 'hitlist': "+ergebnis)
			result=json.loads(ergebnis)
			#print("json")
			if result['status']=='ok':
				# hitlist.extend([[i['description'][0], i['description'][1], i['description'][2], i['url'], i['url'].after('https://entscheidsuche.ch/view/')] for i in result['hitlist']])
				hitlist.extend([[i['description'][0],i['description'][1], i['description'][2],i['url']] for i in result['hitlist']])
			else:
				result['errormodule']="getData return from hitlist-command"	
				status['status']='error'
				saveStatus(status, id)
				return result
			start+=count
			status['fetched']=start
			status['last']=datetime.datetime.fromtimestamp(time.time())
			saveStatus(status, id)
		print("Schreibe CSV")
		with open(dir+"/hitlist.csv", 'w') as f:
			write = csv.writer(f)
			# write.writerow(["Description1","Description2","Description3","URL","ID"])
			write.writerow(["Description1","Description2","Description3","URL"])
			write.writerows(hitlist)
		print('fertig CSV')
		reply['verzeichnis']=verzeichnisname
		status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
		status['status']='done'
		status['erasure']=datetime.datetime.fromtimestamp(time.time()+604800).isoformat()
		saveStatus(status, id)
			
	except:
		reply['errormodule']="getData"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)

	finally:
		return reply

def saveStatus(status,id):
	path=PARENTDIR+"/"+PREDIR+str(id)+"/status.json"
	with open(path, "w") as outfile:
    	outfile.write(json.dumps(status))
	
def load(sdata):
	reply={}
	reply['status']='ok'
	return reply
	
def status(sdata):
	reply['status']='error'
	try:
		if "id" in sdata:
			id=sdata['id']
			path=PARENTDIR+"/"+id+"/status.json"
			if os.path.isfile(path):
				f = open(path)
				data=json.load(f)
				reply.update(data)
				reply['status']='ok'
			else:
				reply['error']='id '+id+' not found'	
		else:
			reply['error']='no id submitted'	
	except:
		reply['error']='no description available'
	finally:
		return reply



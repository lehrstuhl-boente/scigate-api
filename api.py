# function called by the API
import json
import requests
import time
import datetime
import os
import csv
import random
import sys
import traceback
import threading

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
	id=millisec = int(time.time() * 100000000000)+random.randint(0,100000000)

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
					new_thread = thread(target=getData,args=(query,collection,hits,id))
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
	except Exception as ex:
		printException(ex,"search "+str(id))
		reply['errormodule']="search"
		reply['error']="exception caught"	
		reply['status']='error'
	finally:
		return reply
	
def getData(query,collection,hits,id):
	print('Start getData for '+str(id))
	status={ 'start': datetime.datetime.fromtimestamp(id/100000000000.0).isoformat(), 'last': datetime.datetime.fromtimestamp(time.time()).isoformat(), 'hits': hits, 'fetched': 0, 'status': 'running'}
	reply={}
	reply['status']='ok'
	start=0
	hitlist=[]
	verzeichnisname=PREDIR+str(id)
	dir=PARENTDIR+"/"+verzeichnisname
	print("lege nun Verzeichnis '"+dir+"' an.")
	os.mkdir(dir)
	saveStatus(status, id)
	try:
		print('Start getData try for '+str(id))
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
			
	except Exception as ex:
		printException(ex,"getData "+str(id))
		reply['errormodule']="getData"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)

	finally:
		print("finally block of getData for "+str(id))	
		return reply

def printException(ex, name):
	# Get current system exception
	ex_type, ex_value, ex_traceback = sys.exc_info()

	# Extract unformatter stack traces as tuples
	trace_back = traceback.extract_tb(ex_traceback)

	# Format stacktrace
	stack_trace = list()

	for trace in trace_back:
		stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))

	print("Exception "+name)
	print("Exception type : %s " % ex_type.__name__)
	print("Exception message : %s" %ex_value)
	print("Stack trace : %s" %stack_trace)


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
			path=PARENTDIR+"/"+PREDIR+id+"/status.json"
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



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
import zipfile

APIURL="http://v2202109132150164038.luckysrv.de:8080/"
MYAPIURL="http://v2202109132150164038.luckysrv.de:5001/api/"
MYFILEURL="http://v2202109132150164038.luckysrv.de/apidata/"
CHUNK=100
PARENTDIR="/home/jorn/scigateapi/data"
PREDIR="request"
MAXREPLY=200
BASISURL="https://entscheidsuche.ch/docs"

def search(sdata):
	reply={}
	reply['status']='ok'
	# add some random to the id so that guessing it becomes difficult
	id=millisec = int(time.time() * 100000000000)+random.randint(0,100000000)

	try:
		query=sdata['query']
		maxHits=100
		if 'maxHits' in sdata:
			maxHits=sdata['maxHits']
		maxReply=100
		if 'maxReply' in sdata:
			maxReply=sdata['maxReply']
			if maxReply > MAXREPLY:
				maxReply=MAXREPLY
				reply["warning"]="Documents will be fetched asynchronosly. Synchronous requests are limited to "+str(MAXREPLY)+" hits"			

		fehler=processOutputSetting(sdata)
		if fehler:
			reply['error']=fehler
			reply['status']='error'
			reply['errormodule']='search'
			return

		result={}
		data={'engine': collection, 'type': 'search', 'term': query}
		r=requests.post(url=APIURL,json=data)
		ergebnis=r.text
		result=json.loads(ergebnis)
		if result['status']=='ok':
			hits=result['hits']
			reply['hits']=hits
			reply['token']=str(id)
			reply['check']=MYAPIURL+'status?{%22id%22:'+str(id)+'}'
			reply['id']=str(id)
			if hits>maxHits:
				hits=maxHits
				reply['hitsTruncated']=True
			if hits>maxReply:
				new_thread = threading.Thread(target=getData,args=(query,collection,hits,id,sdata))
				new_thread.start()
			else:
				print("Rufe nun getData mit '"+query+"' auf.")
				reply.update(getData(query,collection,hits,id,sdata))
		else:
			result['errormodule']="search: return from search-command"
			return result
	except Exception as ex:
		printException(ex,"search "+str(id))
		reply['errormodule']="search"
		reply['error']="exception caught"	
		reply['status']='error'
	finally:
		return reply
	
def processOutputSetting(sadata):
	if 'collection' in sdata:
		collection=sdata['collection']
		if collection in ['entscheidsuche','boris','zora','swisscovery']:

			#setDefaults
			if not 'getZIP' in sdata:
				sdata['getZIP']=True
			if not 'getDocs' in sdata:
				sdata['getDocs']=False
			if not 'getCSV' in sdata:
				sdata['getCSV']=False
			if not 'getHTML' in sdata:
				sdata['getHTML']=True
			if not 'getJSON' in sdata:
				sdata['getJSON']=False
			if sdata['getDocs'] and collection != 'entscheidsuche':
				return "getDocs only available for entscheidsuche collection"
			if not (sdata['getCSV'] or sdata['getHTML'] or sdata['getJSON'] or sdata['getDocs']):
				return "no output format selected, select at least one of getCSV, getHTML, getJSON, getDocs"

			#always ZIP when retrieving docs
			if 'getDocs' in sdata and sdata['getDocs']:
				sdata['getZIP']=True
		else:
			return "Collection '"+collection+"' unknown"
	else:
		return "no collection set"
		
	return ""
	
	
def getData(query,hits,id,sdata):
	print('Start getData for '+str(id))
	status={ 'start': datetime.datetime.fromtimestamp(id/100000000000.0).isoformat(), 'last': datetime.datetime.fromtimestamp(time.time()).isoformat(), 'hits': hits, 'fetched': 0, 'requeststatus': 'running'}
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
			data={'engine': sdata['collection'], 'type': 'hitlist', 'term': query, 'start':start, 'count': count}
			r=requests.post(url=APIURL,json=data)
			ergebnis=r.text
			#print("Ergebnis von 'hitlist': "+ergebnis)
			result=json.loads(ergebnis)
			#print("json")
			if result['status']=='ok':
				hitlist.extend(result['hitlist'])
			else:
				result['errormodule']="getData return from hitlist-command"	
				status['requeststatus']='error'
				saveStatus(status, id)
				return result
			start+=count
			status['fetched']=start
			status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
			saveStatus(status, id)

		if sdata['getDocs']:
			for t in hitlist:
				url=t['url']
				stamm=url.split('/view/')
				entscheidid=stamm[1]
				stammurl=stamm[0]+"/docs/"+stamm[1]
				stammpath=PARENTDIR+"/"+verzeichnisname+"/"+stamm[1]
				r=requests.get(url=stammurl+".json")
				with open(stammpath+".json", "w") as outfile:
					outfile.write(r.text)
				t['JSON-File']=entscheidid+".json"
				t['JSON-URL']=stammurl+".json"
				print(stammurl+".json")
				entscheidjson=json.loads(r.text)
				if "HTML" in entscheidjson:
					r=requests.get(url=stammurl+".html")
					with open(stammpath+".html", "w") as outfile:
						outfile.write(r.text)
					t['HTML-File']=entscheidid+".html"
					t['HTML-URL']=stammurl+".html"	
				if "PDF" in entscheidjson:
					r=requests.get(url=stammurl+".pdf")
					with open(stammpath+".html", "wb") as outfile:
						outfile.write(r.content)
					t['PDF-File']=entscheidid+".pdf"
					t['PDF-URL']=stammurl+".pdf"
				if "Datum" in entscheidjson:
					t['Date']=entscheidjson['Datum']
				if "Sprache" in entscheidjson:
					t['Lang']=entscheidjson['Sprache']
					lang=entscheidjson['Sprache']
				else:
					lange="de"
				if "Zeit UTC" in entscheidjson:
					t['Scrapingtime UTC']=entscheidjson['Zeit UTC']
				if "Abstract" in entscheidjson:
					t['Scrapingtime UTC']=entscheidjson['Abstract'][0]['Text']
				if "Num" in entscheidjson:
					t['Reference']=entscheidjson['Num']
				if "Meta" in entscheidjson:
					t['Source']=list(filter(lambda x: x['Sprachen'][0] == lang, entscheidjson['Meta']))[0]['Text']
			
		if sdata['getJSON']:
			print("Schreibe JSON")
			with open(dir+"/hitlist.json", 'w') as f:
				f.write(json.dumps(hitlist))
			status['json']=MYFILEURL+verzeichnisname+"/hitlist.json"		
			status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
			saveStatus(status, id)
		
		if sdata['getCSV']:
			print("Schreibe CSV")
			with open(dir+"/hitlist.csv", 'w') as f:
				write = csv.writer(f)
				# write.writerow(["Description1","Description2","Description3","URL","ID"])
				write.writerow(["Description1","Description2","Description3","URL"])
				write.writerows(hitlist)
			status['csv']=MYFILEURL+verzeichnisname+"/hitlist.csv"

		status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
		status['requeststatus']='done'
		status['erasure']=datetime.datetime.fromtimestamp(time.time()+604800).isoformat()
		saveStatus(status, id)
		
		if sdata['getZIP']:
			print("Schreibe ZIP")
			status['zip']=MYFILEURL+verzeichnisname+"/result.zip"
			saveStatus(status, id)
			with zipfile.ZipFile(PARENTDIR+"/"+verzeichnisname+'/result.zip', 'w') as zipObj:
  			# Iterate over all the files in directory
				for folderName, subfolders, filenames in os.walk(PARENTDIR+"/"+verzeichnisname):
					for filename in filenames:
						#create complete filepath of file in directory
						filePath = os.path.join(folderName, filename)
						# Add file to zip
						zipObj.write(filePath, os.path.basename(filePath))
				
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

def loadDocs(hitlist,id,sdata,verzeichnisname):
	print('Start loadDocs for '+str(id))
	hits=len(hitlist)
	status={ 'start': datetime.datetime.fromtimestamp(id/100000000000.0).isoformat(), 'last': datetime.datetime.fromtimestamp(time.time()).isoformat(), 'hits': hits, 'fetched': 0, 'requeststatus': 'running'}
	reply={}
	reply['status']='ok'
	start=0

	saveStatus(status, id)
	try:
		for t in hitlist:
			if 'url' in t:
				url=t['url']
				stamm=url.split('/view/')
				entscheidid=stamm[1]
				basisurl=stamm[0]
				t['DocID']=entscheidid
			else:
				entscheidid=t['DocID']
				basisurl=BASISURL

			stammurl=basisurl+"/docs/"+entscheidid
			stammpath=PARENTDIR+"/"+verzeichnisnme+"/"+entscheidid
			r=requests.get(url=stammurl+".json")
			with open(stammpath+".json", "w") as outfile:
				outfile.write(r.text)
			t['JSON-File']=entscheidid+".json"
			t['JSON-URL']=stammurl+".json"
			print(stammurl+".json")
			entscheidjson=json.loads(r.text)
			if "HTML" in entscheidjson:
				r=requests.get(url=stammurl+".html")
				with open(stammpath+".html", "w") as outfile:
					outfile.write(r.text)
				t['HTML-File']=entscheidid+".html"
				t['HTML-URL']=stammurl+".html"	
			if "PDF" in entscheidjson:
				r=requests.get(url=stammurl+".pdf")
				with open(stammpath+".html", "wb") as outfile:
					outfile.write(r.content)
				t['PDF-File']=entscheidid+".pdf"
				t['PDF-URL']=stammurl+".pdf"
			if "Datum" in entscheidjson:
				t['Date']=entscheidjson['Datum']
			if "Sprache" in entscheidjson:
				t['Lang']=entscheidjson['Sprache']
				lang=entscheidjson['Sprache']
			else:
				lange="de"
			if "Zeit UTC" in entscheidjson:
				t['Scrapingtime UTC']=entscheidjson['Zeit UTC']
			if "Abstract" in entscheidjson:
				t['Scrapingtime UTC']=entscheidjson['Abstract'][0]['Text']
			if "Num" in entscheidjson:
				t['Reference']=entscheidjson['Num']
			if "Meta" in entscheidjson:
				t['Source']=list(filter(lambda x: x['Sprachen'][0] == lang, entscheidjson['Meta']))[0]['Text']
			
		if sdata['getJSON']:
			print("Schreibe JSON")
			with open(dir+"/hitlist.json", 'w') as f:
				f.write(json.dumps(hitlist))
			status['json']=MYFILEURL+verzeichnisname+"/hitlist.json"		
			status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
			saveStatus(status, id)
		
		if sdata['getCSV']:
			print("Schreibe CSV")
			spalten={}
			for h in hitlist:
				for k in h:
					if h[k]==list:
						l=len(h[k])
					else:
						l=1
					if h[k] in spalten:
						if spalten[h[k]]<l:
							spalten[h[k]]=l
					else:
						spalten[h[k]]=l

			spaltenliste=[]
			for s in spalten:
				spaltenliste.append[s]
				if spalten[s]>1:
					i=1
					while spalten[s]>i:
						i++
						spaltenliste.append[s+str(i)]
			spaltenzahl=len(spaltenliste)
			
			with open(dir+"/hitlist.csv", 'w') as f:
				write = csv.writer(f)
				write.writerow(spaltenliste)
				for h in hitlist:
					s=0
					reihe=[]
					while s<spaltenzahl:
						spaltenname=spaltenliste[s]
						if spaltenname in h:
							spaltenwert=h[spaltenname]
							if type(spaltenwert)==list:
								reihe.extend(spaltenwert)
								s+=len(spaltenwert)
							else:
								reihe.append(str(spaltenwert))
								s+=1
						else:
							reihe.append("")
							s+=1
					write.writerow(reihe)
			status['csv']=MYFILEURL+verzeichnisname+"/hitlist.csv"

		status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat()
		status['requeststatus']='done'
		status['erasure']=datetime.datetime.fromtimestamp(time.time()+604800).isoformat()
		saveStatus(status, id)
		
		if sdata['getZIP']:
			print("Schreibe ZIP")
			status['zip']=MYFILEURL+verzeichnisname+"/result.zip"
			saveStatus(status, id)
			with zipfile.ZipFile(PARENTDIR+"/"+verzeichnisname+'/result.zip', 'w') as zipObj:
  			# Iterate over all the files in directory
				for folderName, subfolders, filenames in os.walk(PARENTDIR+"/"+verzeichnisname):
					for filename in filenames:
						#create complete filepath of file in directory
						filePath = os.path.join(folderName, filename)
						# Add file to zip
						zipObj.write(filePath, os.path.basename(filePath))
				
	except Exception as ex:
		printException(ex,"loadDocs "+str(id))
		reply['errormodule']="getData"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)

	finally:
		print("finally block of getData for "+str(id))	
		return reply


def docs(sdata):
	reply={}
	reply['status']='ok'
	# add some random to the id so that guessing it becomes difficult
	id=millisec = int(time.time() * 100000000000)+random.randint(0,100000000)

	try:
		sdata['getDocs']=True
		fehler=processOutputSetting(sdata)
		if fehler:
			reply['error']=fehler
			reply['status']='error'
			reply['errormodule']='docs'
			return

		if 'docids' in sdata:
			hitlist=[{'DocID': i} for i in sdata['docids']]
			zahl=len(hitlist)
			reply['hits']=zahl
			reply['token']=str(id)
			reply['check']=MYAPIURL+'status?{%22id%22:'+str(id)+'}'
			reply['id']=str(id)
			verzeichnisname=PREDIR+str(id)
			dir=PARENTDIR+"/"+verzeichnisname
			print("lege nun Verzeichnis '"+dir+"' an.")
			os.mkdir(dir)

			if zahl>MAXREPLY:
				reply["warning"]="Documents will be fetched asynchronosly. Synchronous requests are limited to "+str(MAXREPLY)+" hits"
				new_thread = threading.Thread(target=loadDocs,args=(hitlist,id,sdata,verzeichnisname))
				new_thread.start()
				
			else:
				print("Rufe nun getData mit '"+query+"' auf.")
				reply.update(loadDocs(hitlist,id,sdata,verzeichnisname))
		else:
			result['errormodule']="docs"
			reply['status']='error'
			reply['error']='Missing document list'			
			return result	
	except Exception as ex:
		printException(ex,"docs "+str(id))
		reply['errormodule']="docs"
		reply['error']="exception caught"	
		reply['status']='error'
	finally:
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
	
	
def status(sdata):
	reply={}
	reply['status']='error'
	try:
		if "id" in sdata:
			id=sdata['id']
			path=PARENTDIR+"/"+PREDIR+str(id)+"/status.json"
			if os.path.isfile(path):
				f = open(path)
				data=json.load(f)
				reply.update(data)
				reply['status']='ok'
			else:
				reply['error']='id '+str(id)+' not found'	
		else:
			reply['error']='no id submitted'	
	except Exception as ex:
		printException(ex,"status")
		reply['error']='no description available'
	finally:
		return reply



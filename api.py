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
import re
import copy

APIURL="http://v2202109132150164038.luckysrv.de/stubs/"
MYAPIURL="http://v2202109132150164038.luckysrv.de/api/"
MYFILEURL="http://v2202109132150164038.luckysrv.de/apidata/"
CHUNK=100
PARENTDIR="/home/jorn/scigateapi/data"
PREDIR="request"
MAXREPLY=100
BASISURL="https://entscheidsuche.ch/docs"
ZIPNAME="result.zip"
TEMPLATEPATH="/home/jorn/scigateapi/template.html"
SPEICHERZEITRAUM=604800
reDir=re.compile('^request(?P<Zeit>[0-9]{10})[0-9]{11}$')

TEMPLATEKEYS=["query","hits","truncated","checked_entscheidsuche","checked_swisscovery","checked_zora","checked_swisslexGreen","checked_repositorium","checked_boris","checked_fedlex","checked_csv","checked_json","checked_html","checked_nicehtml","checked_docs","checked_zip","maxhits","maxreply","filter"]
# Wollte Semaphores nehmen für den Zugriff auf Status. Geht aber einfacher. Wenn der Status noch im Speicher ist, kann er aus dem Speicher genommen werden. Falls nicht, gibt es auch keine Zugriffskonflikte
# Semaphores={}
Status={}

HTMLSTART="""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <style>
		.styled-table {
			border-collapse: collapse;
			margin: 25px 0;
			font-size: 0.9em;
			font-family: sans-serif;
			min-width: 400px;
			box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
		}
		.styled-table thead tr {
			background-color: #009879;
			color: #ffffff;
			text-align: left;
		}
		.styled-table tbody tr {
			border-bottom: 1px solid #dddddd;
		}
		.styled-table tbody tr:nth-of-type(even) {
			background-color: #f3f3f3;
		}
		.styled-table tbody tr:last-of-type {
			border-bottom: 2px solid #009879;
		}
		.styled-table tbody tr.active-row {
			font-weight: bold;
			color: #009879;
		}
	</style>
  </head>
  <body>"""

def search(sdata):
	print("search:",sdata)
	p={ a: "" for a in TEMPLATEKEYS}
	reply={}
	reply['status']='ok'
	# add some random to the id so that guessing it becomes difficult
	id= int(time.time() * 100000000000)+random.randint(0,100000000)
	# Semaphores are needed to make sure that only complete status files are read
	# Semaphores[id]=threading.Semaphore(1)

	try:
		if 'query' in sdata:
			query=sdata['query']
		else:
			query=""
		p['query']=query
		if 'filter' not in sdata:
			sdata['filter']=""
		filter=sdata['filter']
		p['filter']=filter.replace('@','&quot;')
		maxHits=200
		if 'maxHits' in sdata:
			maxHits=sdata['maxHits']
			if isinstance(maxHits,str):
				maxHits=int(maxHits)
		p['maxhits']=maxHits
		maxReply=100
		if 'maxReply' in sdata:
			maxReply=sdata['maxReply']
			if isinstance(maxReply,str):
				maxReply=int(maxReply)
			if maxReply > MAXREPLY:
				maxReply=MAXREPLY
				reply["warning"]="Documents will be fetched asynchronosly. Synchronous requests are limited to "+str(MAXREPLY)+" hits"			
		p['maxreply']=maxReply
		fehler=processOutputSetting(sdata,p)
		if fehler:
			reply['error']=fehler
			reply['status']='error'
			reply['errormodule']='search'
			return reply
			
		p['checked_'+sdata['collection']]='checked'

		result={}
		data={'engine': sdata['collection'], 'type': 'search', 'term': query, 'filter': filter}
		r=requests.post(url=APIURL,json=data)
		ergebnis=r.text
		result=json.loads(ergebnis)
		if result['status']=='ok':
			hits=result['hits']
			print("Hits in search:", hits)
			reply['hits']=hits
			reply['maxHits']=maxHits
			reply['token']=str(id)
			reply['check']=MYAPIURL+'status?{%22id%22:'+str(id)+'}'
			reply['id']=str(id)
			if hits>maxHits:
				p['hits']=str(maxHits)+' of '+str(hits)
				hits=maxHits
				reply['hitsTruncated']=True
				print("Reply:", reply)
			else:
				p['hits']=str(hits)
			if sdata['ui']:
				with open(TEMPLATEPATH) as f:
					htmlstring = f.readlines()
				reply['htmloutput']=("".join(htmlstring)).format(**p)
			else:			
				if hits>maxReply:
					print("Rufe nun getData in neuem Thread mit '"+query+"' auf.")
					new_thread = threading.Thread(target=getData,args=(query,hits,id,sdata))
					new_thread.start()
					reply["requeststatus"]="running"
				else:
					print("Rufe nun getData mit '"+query+"' auf.")
					reply.update(getData(query,hits,id,sdata))
			return reply
		else:
			result['errormodule']="search: return from search-command"
			print("-3-", result)	
			return result
	except Exception as ex:
		printException(ex,"search "+str(id))
		reply['errormodule']="search"
		reply['error']="exception caught"	
		reply['status']='error'
		return reply
	
def checkExpiry():
	limit=int(time.time())-SPEICHERZEITRAUM
	dateien=os.listdir(PARENTDIR)
	for datei in dateien:
		f=reDir.match(datei)
		if f and int(f.group('Zeit'))<limit:
			os.system('rm -rf '+PARENTDIR+"/"+datei)
			
	
def processOutputSetting(sdata,p):
	checkExpiry()
	if not 'collection' in sdata:
		sdata['collection']='entscheidsuche'

	collection=sdata['collection']
		
	if collection in ['entscheidsuche','boris','zora','swisscovery','fedlex','swisslexGreen','repositorium']:
		#setDefaults
		if not 'getZIP' in sdata:
			sdata['getZIP']=True
		else:
			p['checked_zip']='checked'
		if not 'getDocs' in sdata:
			sdata['getDocs']=False
		elif sdata['getDocs']:
			p['checked_docs']='checked'
		if not 'getCSV' in sdata:
			sdata['getCSV']=False
		else:
			p['checked_csv']='checked'
		if 'getNiceHTML' in sdata:
			sdata['getNiceHTML']=True
			p['checked_nicehtml']='checked'
		if not 'getHTML' in sdata:
			sdata['getHTML']=False
		else:
			p['checked_html']='checked'
		if not 'getJSON' in sdata:
			sdata['getJSON']=False
		else:
			p['checked_json']='checked'
		if not 'ui' in sdata:
			sdata['ui']=True
		if sdata['getDocs'] and collection != 'entscheidsuche':
			return "getDocs only available for entscheidsuche collection"
		if not (sdata['getCSV'] or sdata['getHTML'] or sdata['getJSON'] or sdata['getDocs'] or sdata['ui']):
			return "no output format selected, select at least one of getCSV, getHTML, getNiceHTML, getJSON, getDocs or set ui"

		#always ZIP when retrieving docs
		if sdata['getDocs']:
			sdata['getZIP']=True
		if sdata['getZIP']:
			p['checked_zip']='checked'
	
	else:
		return "Collection '"+collection+"' unknown"
		
	return ""
	
	
def getData(query,hits,id,sdata):
	print('Start getData for '+str(id))
	status={ 'hits': hits, 'fetched': 0, 'requeststatus': 'running', 'job': 'reading hitlist'}
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
			data={'engine': sdata['collection'], 'type': 'hitlist', 'term': query, 'filter': sdata['filter'], 'start':start, 'count': count}
			print(data)
			
			r=requests.post(url=APIURL,json=data)
			#print("Ergebnis von 'hitlist': "+ergebnis)
			retries=0
			while r.status_code != 200 and retries < 10:
				retries += 1
				print ("Status code: "+str(r.status_code)+" '"+r.text+"' Retry "+str(retries))
				r=requests.post(url=APIURL,json=data)
				
			ergebnis=r.text
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
			saveStatus(status, id)

		reply.update(loadDocs(hitlist,id,sdata,verzeichnisname))
		return reply
				
	except Exception as ex:
		printException(ex,"getData "+str(id))
		reply['errormodule']="getData"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)
		return reply

def loadDocs(hitlist,id,sdata,verzeichnisname):
	print('Start loadDocs for '+str(id))
	reply={}
	reply['status']='ok'
	hits=len(hitlist)
	status={ 'hits': hits, 'fetched': 0, 'requeststatus': 'running', 'job': 'loadDocs', 'errlist': []}
	saveStatus(status, id)

	try:
		if sdata['getDocs']:
			reply,fetched=getDocs(hitlist, id,sdata,verzeichnisname)
			status['fetched']=fetched
			if reply['status']!='ok':
				status['errlist'].append(reply['errlist'])
			
		if sdata['getJSON']:
			reply=writeJSON(hitlist, id, sdata, verzeichnisname)
			if reply['status']!='ok':
				status['errlist'].append(reply['errlist'])

		if sdata['getCSV'] or sdata['getHTML']:
			reply=writeCSV_HTML(hitlist, id, sdata, verzeichnisname)
			if reply['status']!='ok':
				status['errlist'].append(reply['errlist'])

		status['requeststatus']='done'
		status['erasure']=datetime.datetime.fromtimestamp(time.time()+SPEICHERZEITRAUM).isoformat(timespec="minutes", sep=" ")
		saveStatus(status, id)
		
		if sdata['getZIP']:
			status['job']="creating ZIP"
			saveStatus(status, id)
			print("Schreibe ZIP")
			status['zip']=MYFILEURL+verzeichnisname+"/"+ZIPNAME
			saveStatus(status, id)
			with zipfile.ZipFile(PARENTDIR+"/"+verzeichnisname+'/'+ZIPNAME, 'w') as zipObj:
  			# Iterate over all the files in directory
				for folderName, subfolders, filenames in os.walk(PARENTDIR+"/"+verzeichnisname):
					for filename in filenames:
						#create complete filepath of file in directory
						filePath = os.path.join(folderName, filename)
						# Add file to zip
						if filename!=ZIPNAME:
							print("Zippe Datei "+filename+" in "+folderName)
							zipObj.write(filePath, os.path.basename(filePath))
			reply['zip']=MYFILEURL+verzeichnisname+"/"+ZIPNAME
		status['job']=""
		saveStatus(status, id)
		reply['requeststatus']='done'
		return reply
				
	except Exception as ex:
		printException(ex,"loadDocs "+str(id))
		reply['errormodule']="loadDocs"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)
		reply['requeststatus']='error'
		return reply


def getDocs(hitlist,id,sdata,verzeichnisname):
	print('Start getDocs for '+str(id))
	hits=len(hitlist)
	reply={}
	reply['status']='ok'
	reply['errlist']=[]

	status={ 'hits': hits, 'fetched': 0, 'requeststatus': 'running', 'job': 'reading documents', 'errlist': []}
	saveStatus(status, id)
	start=0
	entfernt=0
	skiplist=[]
	for idx in range(len(hitlist)):
		t=hitlist[idx-entfernt]
		error=getDocsSub(t,id,verzeichnisname)
		if error:
			status['errlist'].append(error)
			reply['errlist'].append(error)
			skiplist.append(hitlist[idx-entfernt])
			del hitlist[idx-entfernt]
			entfernt+=1
			status['status']='warning'
			saveStatus(status, id)
			reply['requeststatus']='warning'
			
		if idx % 10 ==5:
			status['fetched']=idx-entfernt
			status['skipped']=entfernt
			saveStatus(status,id)

	if entfernt>0:
		print("Probiere nun "+str(entfernt)+" fehlgeschlagene Entscheide erneut.")
		for idx in range(len(skiplist)):
			t=hitlist[idx]
			error=getDocsSub(t,id,verzeichnisname)
			if error:
				status['errlist'].append(error)
				reply['errlist'].append(error)
			else:
				entfernt-=1
				meldung="Zweitversuch für "+t['DocID']+" erfolgreich."				
				status['errlist'].append(meldung)
				reply['errlist'].append(meldung)
				print(meldung)
				hitlist.append(t)
			
		if entfernt==0:
			status['status']='ok'
			reply['requeststatus']='ok'
	status['fetched']=len(hitlist)
	status['skipped']=entfernt
	saveStatus(status,id)

	return reply, len(hitlist)


	
def getDocsSub(t,id,verzeichnisname):
	entscheidid="undefined"
	try:
		if 'url' in t:
			url=t['url']
			stamm=url.split('/view/')
			entscheidid=stamm[1]
			basisurl=stamm[0]
			t['DocID']=entscheidid
		else:
			entscheidid=t['DocID']
			basisurl=BASISURL

		print("Verarbeite "+entscheidid)
		stammurl=basisurl+"/docs/"+entscheidid
		stammpath=PARENTDIR+"/"+verzeichnisname+"/"+entscheidid
		r=requests.get(url=stammurl+".json")
		with open(stammpath+".json", "w") as outfile:
			outfile.write(r.text)
		t['JSON-File']=entscheidid+".json"
		t['JSON-URL']=stammurl+".json"
		print(stammurl+".json")
		if len(r.text)<10:
			error="File "+stammurl+".json was (almost) empty. Skipping item from hitlist"
		else:
			error=""
			entscheidjson=json.loads(r.text)
			if "HTML" in entscheidjson:
				r=requests.get(url=stammurl+".html")
				with open(stammpath+".html", "wb") as outfile:
					outfile.write(r.content)
				t['HTML-File']=entscheidid+".html"
				t['HTML-URL']=stammurl+".html"	
			if "PDF" in entscheidjson:
				r=requests.get(url=stammurl+".pdf")
				with open(stammpath+".pdf", "wb") as outfile:
					outfile.write(r.content)
				t['PDF-File']=entscheidid+".pdf"
				t['PDF-URL']=stammurl+".pdf"
			if "Datum" in entscheidjson:
				t['Date']=entscheidjson['Datum']
			if "Sprache" in entscheidjson:
				t['Lang']=entscheidjson['Sprache']
				lang=entscheidjson['Sprache']
			else:
				lang="de"
			if "Zeit UTC" in entscheidjson:
				t['Scrapingtime UTC']=entscheidjson['Zeit UTC']
			if "Abstract" in entscheidjson:
				t['Abstract']=entscheidjson['Abstract'][0]['Text']
			if "Num" in entscheidjson:
				t['Reference']=entscheidjson['Num']
			if "Meta" in entscheidjson:
				t['Source']=list(filter(lambda x: x['Sprachen'][0] == lang, entscheidjson['Meta']))[0]['Text']
		return error

	except Exception as ex:
		detail=printException(ex,"getDocs "+str(id)+" "+entscheidid)
		error="Exception with loading document "+entscheidid+" skipping item from hitlist ["+detail+"]"
		return error

def writeJSON(hitlist,id,sdata,verzeichnisname):
	print('Start writeJSON for '+str(id))
	hits=len(hitlist)
	reply={}
	reply['status']='ok'

	try:
		print("Schreibe JSON")
		status={ 'hits': hits, 'fetched': hits, 'requeststatus': 'running', 'job': 'creating JSON'}
		saveStatus(status, id)
		with open(PARENTDIR+"/"+verzeichnisname+"/hitlist.json", 'w') as f:
			# der komplette dump führt zum Fehler
			# f.write(json.dumps(hitlist))
			f.write("[")
			for i in range(len(hitlist)-1):
				f.write(json.dumps(hitlist[i]))
				f.write(",")
			f.write(json.dumps(hitlist[len(hitlist)-1]))
			f.write("]")	
		status['json']=MYFILEURL+verzeichnisname+"/hitlist.json"		
		reply['json']=MYFILEURL+verzeichnisname+"/hitlist.json"	
		saveStatus(status, id)
		return reply

	except Exception as ex:
		printException(ex,"writeJSON "+str(id))
		reply['errormodule']="writeJSON"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)
		reply['requeststatus']='error'
		reply['errlist']=printException(ex,"writeJson "+str(id)+" "+entscheidid)
		return reply



def writeCSV_HTML(hitlist,id,sdata,verzeichnisname):
	print('Start writeCSV_HTML for '+str(id))
	hits=len(hitlist)
	reply={}
	reply['status']='ok'

	try:
		print("Bereite CSV und/oder HTML vor")
		spalten={}
		for h in hitlist:
			for k in h:
				if k != 'sort':
					if type(h[k])==list:
						#leere Einträge am Ende löschen
						l=len(h[k])
						while l>1 and not h[k][l-1]:
							l-=1
							del h[k][l]
					else:
						l=1
					if k in spalten:
						if spalten[k]<l:
							spalten[k]=l
					else:
						spalten[k]=l
		print(spalten)

		spaltenliste=[]
		for s in spalten:
			spaltenliste.append(s)
			if spalten[s]>1:
				i=1
				while spalten[s]>i:
					i+=1
					spaltenliste.append(s+str(i))
		spaltenzahl=len(spaltenliste)
		
		print(spaltenliste)
		
		if sdata['getCSV']:
			print("Schreibe CSV")
			status={ 'hits': hits, 'fetched': hits, 'requeststatus': 'running', 'job': 'creating CSV'}
			with open(PARENTDIR+"/"+verzeichnisname+"/hitlist.csv", 'w') as f:
				write = csv.writer(f)
				write.writerow(spaltenliste)
				for h in hitlist:
					s=0
					reihe=[]
					while s<spaltenzahl:
						spaltenname=spaltenliste[s]
						if spaltenname !='sort':
							if spaltenname in h:
								spaltenwert=h[spaltenname]
								if type(spaltenwert)==list:
									reihe.extend(spaltenwert)
									s+=len(spaltenwert)
								else:
									reihe.append(spaltenwert)
									s+=1
							else:
								reihe.append("")
								s+=1
					write.writerow(reihe)
			status['csv']=MYFILEURL+verzeichnisname+"/hitlist.csv"
			reply['csv']=MYFILEURL+verzeichnisname+"/hitlist.csv"

		if sdata['getHTML']:
			print("Schreibe HTML")
			status={ 'hits': hits, 'fetched': hits, 'requeststatus': 'running', 'job': 'creating CSV'}
			with open(PARENTDIR+"/"+verzeichnisname+"/hitlist.html", 'w') as f:
				f.write(HTMLSTART)
				f.write("<table class='styled-table'><thead><tr><th>")
				f.write("</th><th>".join(spaltenliste))
				f.write("</th></tr></thead>")
				f.write("<tobody>")
				for h in hitlist:
					f.write("<tr>")
					s=0
					while s<spaltenzahl:
						spaltenname=spaltenliste[s]
						if spaltenname !='sort':
							if spaltenname in h:
								spaltenwert=h[spaltenname]
								if type(spaltenwert)==list:
									f.write("<td>"+"</td><td>".join(spaltenwert)+"</td>")
									s+=len(spaltenwert)
								else:
									if spaltenwert[:4]=="http":
										spaltenwert="<a href='"+spaltenwert+"'>"+spaltenwert+"</a>"
									f.write("<td>"+spaltenwert+"</td>")
									s+=1
							else:
								f.write("<td></td>")
								s+=1
					f.write("</tr>")
				f.write("</tbody></table></body></html>")
				status['html']=MYFILEURL+verzeichnisname+"/hitlist.html"
				reply['html']=MYFILEURL+verzeichnisname+"/hitlist.html"
		return reply			
				
	except Exception as ex:
		printException(ex,"writeCSV_HTML "+str(id))
		reply['errormodule']="writeCSV_HTML"
		reply['error']="exception caught"	
		reply['status']='error'
		status['status']='error'
		saveStatus(status, id)
		reply['requeststatus']='error'
		reply['errlist']=printException(ex,"writeCSV_HTML "+str(id)+" "+entscheidid)
		return reply


def docs(sdata):
	reply={}
	reply['status']='ok'
	# add some random to the id so that guessing it becomes difficult
	id= int(time.time() * 100000000000)+random.randint(0,100000000)
	# Semaphores are needed to make sure that only complete status files are read
	# Semaphores[id]=Semaphore(1)


	try:
		sdata['getDocs']=True
		p={ a: "" for a in TEMPLATEKEYS}
		fehler=processOutputSetting(sdata,p)
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
			verzeichnisname=PREDIR+str(id)
			dir=PARENTDIR+"/"+verzeichnisname
			print("lege nun Verzeichnis '"+dir+"' an.")
			os.mkdir(dir)

			if zahl>MAXREPLY:
				new_thread = threading.Thread(target=loadDocs,args=(hitlist,id,sdata,verzeichnisname))
				new_thread.start()
				reply["running"]=True
				
			else:
				print("Rufe nun getData mit '"+query+"' auf.")
				reply.update(loadDocs(hitlist,id,sdata,verzeichnisname))

		else:
			result['errormodule']="docs"
			reply['status']='error'
			reply['error']='Missing document list'			
			return result	
		return reply
	except Exception as ex:
		printException(ex,"docs "+str(id))
		reply['errormodule']="docs"
		reply['error']="exception caught"	
		reply['status']='error'
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
	
	errstring="Exception "+name+"; Exception type : "+ str(ex_type.__name__) + "; Exception message : "+ str(ex_value)+"; Stack trace : "+",".join(stack_trace)
	
	return errstring



def saveStatus(status,id):
	status['last']=datetime.datetime.fromtimestamp(time.time()).isoformat(timespec="seconds", sep=" ")
	status['start']=datetime.datetime.fromtimestamp(id/100000000000.0).isoformat(timespec="seconds", sep=" ")
	path=PARENTDIR+"/"+PREDIR+str(id)+"/status.json"
	# print("Semaphore acquire status write ",id)
	# Semaphores[id].acquire()
	with open(path, "w") as outfile:
		print("Schreibe ",status)
		outfile.write(json.dumps(status))
	Status[id]=copy.deepcopy(status)
	# print("Semaphore release status write ",id)
	# Semaphores[id].release()
	
	
	
def status(sdata):
	reply={}
	reply['status']='error'
	try:
		if "id" in sdata:
			id=sdata['id']
			if id in Status:
				reply.update(Status[id])
				reply['status']='ok'
			else:
				path=PARENTDIR+"/"+PREDIR+str(id)+"/status.json"
				if os.path.isfile(path):
					# Script might be restarted so that Semaphore is lost and no writing is taking place anymore
					# print("Semaphore acquire status read ",id)
					# if id in Semaphores: Semaphores[id].acquire()
					f = open(path)
					data=json.load(f)
					reply.update(data)
					reply['status']='ok'
					# print("Semaphore release status read ",id)
					# if id in Semaphores : Semaphores[id].release()
				else:
					reply['error']='id '+str(id)+' not found'	
		else:
			reply['error']='no id submitted'	
	except Exception as ex:
		printException(ex,"status")
		reply['error']='no description available'
	finally:
		return reply



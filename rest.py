from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
import threading
import time
import datetime
import json
import api
import urllib.parse

hostName = ""
serverPort = 5001

class MyServer(BaseHTTPRequestHandler):
	def do_OPTIONS(self):
		self.send_response(204,"ok")
		self.send_header('Access-Control-Allow-Credentials', 'true')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
		self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type, Origin, Accept")
		self.send_header("Access-Control-Max-Age", "86400")
		self.end_headers()
		
	def do_GET(self):
		try:
			commands=self.path.split("?",1)
			print(commands)
			if len(commands)<2:
				sdata={}
			else:
				args=urllib.parse.unquote(commands[1])
				print(args)
				sdata=json.loads(args)
			command=commands[0]
		except Exception as ex:
			api.printException(ex,"do_Get")
			self.do_Error('Wrong command: '+self.path+'. Use JSON-Syntax with double quotes.')
		else:
			if command[:5]=="/api/":
				self.do_Common(command,sdata)
			else:
				print("unknown command "+ command)
	
	def do_POST(self):
		try:
			commands=self.path.split("?",1)
			command=commands[0]
			if "application/json" in self.headers.get("Content-type").lower():
				data = self.rfile.read(int(self.headers.get('Content-Length')))
				sdata=json.loads(data)
			else:
				self.do_Error('Wrong Content-type: '+self.headers.get("Content-type")+' (should by application/json)')
		except Exception as ex:
			api.printException(ex,"do_Post")
			self.do_Error('Wrong command: '+self.path)
		else:
			self.do_Common(command,sdata)
			
	def do_Header(self, contenttype="application/json"):
		self.send_response(200)
		self.send_header("Content-type", contenttype+"; charset=utf-8")
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
		self.send_header('Access-Control-Allow-Methods', 'PUT, POST, GET, DELETE, OPTIONS');
		self.end_headers()

	def do_Error(self,fehler):
		self.do_Header()
		reply={}
		reply['status']='error'
		reply['error']=fehler
		string=json.dumps(reply, ensure_ascii=False).encode('utf8')
		self.wfile.write(string)
		
	def do_Common(self,command,sdata):
		reply={}
		reply['status']='ok'
		reply['command']=command
		if command=='/api/search':
			reply=api.search(sdata)
		elif command=='/api/status':
			reply=api.status(sdata)
		elif command=='/api/ui':
			sdata['ui']=True
			reply=api.search(sdata)			
		else:
			reply['status']='error'
			reply['error']="Unknown command: "+command
		if "htmloutput" in reply:
			self.do_Header(contenttype="text/html")
			string=reply['htmloutput'].encode('utf8')
		else:
			self.do_Header()
			string=json.dumps(reply, ensure_ascii=False).encode('utf8')
		self.wfile.write(string)
		
		
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    #server.serve_forwever()
    
if __name__ == "__main__":        
    webServer = ThreadedHTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")

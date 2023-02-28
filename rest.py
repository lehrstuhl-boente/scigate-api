from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import time
import json
import api

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
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		with open("index.html") as f:
			lines = f.readlines()
		f.close()
		for i in lines:
			self.wfile.write(bytes(i, "utf-8"))

	def do_POST(self):
		self.send_response(200)
		self.send_header("Content-type", "application/json; charset=utf-8")
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
		self.send_header('Access-Control-Allow-Methods', 'PUT, POST, GET, DELETE, OPTIONS');
		self.end_headers()
		reply={}
		if "application/json" in self.headers.get("Content-type").lower():
			data = self.rfile.read(int(self.headers.get('Content-Length')))
			sdata=json.loads(data)
			if 'engine' in sdata:
				engine=sdata['engine']
				if engine=='entscheidsuche':
					reply=entscheidsuche.execute(sdata)
				elif engine=='boris':
					reply=boris.execute(sdata)
				elif engine=='zora':
					reply=zora.execute(sdata)
				elif engine=='swisscovery':
					reply=swisscovery.execute(sdata)
				else:
					reply['error']='engine '+engine+' unknown'
		else:
			reply['error']='unexpected Content-type: '+self.headers.get("Content-type")
		if 'error' in reply:
			reply['status']='error'
		else:
			reply['status']='ok'
		string=json.dumps(reply, ensure_ascii=False).encode('utf8')
		print(string);
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

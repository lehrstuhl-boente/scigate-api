parameter={};
baseref=location.protocol+"//"+location.host+"/api/search";

function init(){
	update_parameter();
	if(!(parameter['getDocs'] ||parameter['getCSV'] || parameter['getHTML'] || parameter['getNiceHTML'] || parameter['getJSON'])){
		if(parameter['collection']=='entscheidsuche'){
			document.getElementById('getDocs').checked=true;
		}
		else {
			document.getElementById('getNiceHTML').checked=true;
		}
	}	
}

function update_parameter(){
	parameter['collection']=document.querySelector('input[name="collection"]:checked').value;
	parameter['query']=document.getElementById('searchterm').value;
	parameter['maxHits']=document.getElementById('maxHits').value;
	parameter['maxReply']=document.getElementById('maxReply').value;
	parameter['getDocs']=document.getElementById('getDocs').checked;
	parameter['getCSV']=document.getElementById('getCSV').checked;
	parameter['getHTML']=document.getElementById('getHTML').checked;
	parameter['getNiceHTML']=document.getElementById('getNiceHTML').checked;
	parameter['getJSON']=document.getElementById('getJSON').checked;
	parameter['getZIP']=document.getElementById('getZIP').checked;
	parameter['ui']=false;
	parameterstring=JSON.stringify(parameter);
	document.getElementById('jsonstring').innerHTML=parameterstring.replace(/,"/g,', "');
	return parameterstring;
}

function run_query(){
	update_parameter();
	document.getElementById("replytitle").innerHTML="running...";	
	document.getElementById("reply").innerHTML="";	
	postData(url=baseref, data=parameter).then((data) => {
		if (data['status']!='ok'){
			document.getElementById("replytitle").innerHTML="Error";		
		}
		else{
			if(data['running']){
				document.getElementById("replytitle").innerHTML="Processing asynchronously";		
			}
			else{				
				document.getElementById("replytitle").innerHTML="Request terminated successfully";		
			}
			hits=data['hits']
			if ("hitsTruncated" in data){
				hits = data['maxHits']+" of "+hits;
			}
			document.getElementById("hits").innerHTML=hits;
			reply=JSON.stringify(data).replace(/,"/g,', "');
		}
		document.getElementById("reply").innerHTML=reply;		
	});
}

async function postData(url = "", data = {}) {
  // Default options are marked with *
  const response = await fetch(url, {
    method: "POST", // *GET, POST, PUT, DELETE, etc.
    mode: "cors", // no-cors, *cors, same-origin
    cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
    credentials: "same-origin", // include, *same-origin, omit
    headers: {
      "Content-Type": "application/json",
      // 'Content-Type': 'application/x-www-form-urlencoded',
    },
    redirect: "follow", // manual, *follow, error
    referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
    body: JSON.stringify(data), // body data type must match "Content-Type" header
  });
  return response.json(); // parses JSON response into native JavaScript objects
}

init();
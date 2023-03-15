parameter={};

function init(){
	update_parameter();
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
}

init();
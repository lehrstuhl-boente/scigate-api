function init(){
    set_urls();
}

function set_urls(){
	urlstart=location.protocol+'//'+location.hostname+'/api/';
	document.getElementById('logo').src=urlstart+'logo.svg';
	document.getElementById('css').href=urlstart+'index.css';
}
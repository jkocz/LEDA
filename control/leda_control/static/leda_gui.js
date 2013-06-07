
var xmlhttp;
function loadAJAXDoc(url, cfunc) {
	if (window.XMLHttpRequest) {
		xmlhttp = new XMLHttpRequest();
	}
	xmlhttp.onreadystatechange = cfunc;
	xmlhttp.open("GET",url,true);
	xmlhttp.send();
}

function send(data) {
	loadAJAXDoc("ajax?"+data, function() {
		if (xmlhttp.readyState==4 && xmlhttp.status==200) {
			return xmlhttp.responseText;
		}
	});
}
function request(params, func) {
	loadAJAXDoc("ajax?"+params, function() {
		if (xmlhttp.readyState==4 && xmlhttp.status==200) {
			func(xmlhttp.responseText);
		}
	});
}

status_img = function(status) {
	if( status == 'down') {
		return "static/icons/cross.png";
	}
	else if( status == 'ok' ) {
		return "static/icons/tick.png";
	}
	else if( status == 'error' ) {
		return "static/icons/error.png";
	}
	else {
		return "";
	}
}

vis_image = "roach01_adc01";
vis_image_number = 0;

function onStatusUpdate(response) {
	leda = JSON.parse(response);
	
	img_src = status_img(leda.headnode.alive);
	document.getElementById("headnode_alive_status").src = img_src;
	img_src = status_img(leda.headnode.control);
	document.getElementById("headnode_control_status").src = img_src;
	
	for( var i=0; i<leda.roach.length; ++i ) {
		img_src = status_img(leda.roach[i].flow);
		document.getElementById("roach_status"+i).src = img_src;
	}
	
	for( var i=0; i<leda.control.length; ++i ) {
		for( var j=0; j<leda.control[i][1].length; ++j ) {
			/*name = leda.control[i][0]*/
			img_src = status_img(leda.control[i][1][j].capture);
			document.getElementById("control_capture_status"+i+"_"+j).src = img_src;
			img_src = status_img(leda.control[i][1][j].unpack);
			document.getElementById("control_unpack_status"+i+"_"+j).src = img_src;
			img_src = status_img(leda.control[i][1][j].xengine);
			document.getElementById("control_xengine_status"+i+"_"+j).src = img_src;
			img_src = status_img(leda.control[i][1][j].disk);
			document.getElementById("control_disk_status"+i+"_"+j).src = img_src;
			
			disk_usage = leda.control[i][1][j].disk_info.percent;
			document.getElementById("control_disk_usage"+i+"_"+j).innerHTML = disk_usage;
		}
	}
	
	if( leda.roach.length && leda.roach[0].flow=='ok' ) {
		/*document.getElementById("total_power_enabled").disabled = "disabled";*/
		/*document.getElementById("total_power").disabled = "disabled";*/
		document.getElementById("total_power_enabled").disabled = true;
		document.getElementById("total_power").disabled = true;
	}
	else {
		document.getElementById("total_power_enabled").disabled = false;
		document.getElementById("total_power").disabled = false;
	}
}
function setVisImage() {
	img_src = "static/images/" + vis_image + ".png";
	// Append date to prevent caching
	//img_src += "?" + new Date().getTime();
	img_src += "?" + vis_image_number;
	document.getElementById("minivis").src = img_src;
}
function onImageUpdate(response) {
	if( response == "ok" ) {
		vis_image_number += 1;
		setVisImage();
	}
	else {
		
	}
}
function onStartObsClick(event) {
	if( document.getElementById("total_power_enabled").checked == true ) {
		ncycles = document.getElementById("total_power").value;
		send("total_power="+ncycles);
	}
	else {
		send("total_power=0");
	}
	send("start=1");
}
function onStopObsClick(event)  { send("stop=1"); }
function onKillObsClick(event)  { send("kill=1"); }
function onProgramRoachesClick(event) { send("program_roaches=1"); }
function onCreateBuffersClick(event) { send("create_buffers=1"); }
function onVisModeClick(event)  { vis_image = this.value; setVisImage(); }
function requestStatus() { request("status=1", onStatusUpdate); }
function updateImages() { request("adc_images=1&vismatrix_images=1", onImageUpdate);
						  /*request("vismatrix_images=1", onImageUpdate);*/ }

function main() {
	document.getElementById("start_obs").onclick = onStartObsClick;
	document.getElementById("stop_obs").onclick  = onStopObsClick;
	document.getElementById("kill_obs").onclick  = onKillObsClick;
	document.getElementById("program_roaches").onclick  = onProgramRoachesClick;
	document.getElementById("create_buffers").onclick  = onCreateBuffersClick;
	document.getElementById("vis_roach1_adc1").checked = 1;
	document.getElementById("vis_roach1_adc1").onclick = onVisModeClick;
	document.getElementById("vis_roach1_adc2").onclick = onVisModeClick;
	document.getElementById("vis_roach2_adc1").onclick = onVisModeClick;
	document.getElementById("vis_roach2_adc2").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str1").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str2").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str3").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str4").onclick = onVisModeClick;
	
	requestStatus();
	updateImages();
	setInterval(requestStatus, 5000);
	setInterval(updateImages, 10000);
}

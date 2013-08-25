
function swipeProcessingRoutine() {
	var swipedElement = document.getElementById(triggerElementID);
	
	var container = document.getElementById("tabContainer");
	var npages = container.querySelectorAll(".tabpage").length;
	var navitem = container.querySelector(".tabs ul li");
	var current = parseInt(navitem.parentNode.getAttribute("data-current"));
	
	if ( swipeDirection == 'right' ) {
		var next = current - 1;
		if( next < 1 ) {
			next = 1;
		}
		//var tabs = container.querySelectorAll(".tabs ul li");
		//var tab = tabs[next-1];
		var tab = document.getElementById("tabHeader_" + next);
		tab.onclick.apply(tab);
		
		//swipedElement.style.backgroundColor = 'orange';
	} else if ( swipeDirection == 'left' ) {
		var next = current + 1;
		if( next > npages ) {
			next = npages;
		}
		//var tabs = container.querySelectorAll(".tabs ul li");
		//tabs[next-1].onclick();
		var tab = document.getElementById("tabHeader_" + next);
		tab.onclick.apply(tab);
		
		//swipedElement.style.backgroundColor = 'green';
	} else if ( swipeDirection == 'up' ) {
		//swipedElement.style.backgroundColor = 'maroon';
	} else if ( swipeDirection == 'down' ) {
		//swipedElement.style.backgroundColor = 'purple';
	}
}

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

/*vis_image = "roach01_adc01";*/
vis_image = "latest_vis";
vis_mode  = "stand";
vis_image_number = 0;

function onStatusUpdate(response) {
	leda = JSON.parse(response);
	//console.log(response);
	//leda = response;
	
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
			img_src = status_img(leda.control[i][1][j].buffers);
			document.getElementById("control_buffers_status"+i+"_"+j).src = img_src;
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
			
			capture_receiving = leda.control[i][1][j].capture_info.receiving;
			document.getElementById("control_capture_receiving"+i+"_"+j).innerHTML = capture_receiving;
			capture_dropping = leda.control[i][1][j].capture_info.dropping;
			document.getElementById("control_capture_dropping"+i+"_"+j).innerHTML = capture_dropping;
			capture_dropped = leda.control[i][1][j].capture_info.dropped;
			document.getElementById("control_capture_dropped"+i+"_"+j).innerHTML = capture_dropped;
			
			val = leda.control[i][1][j].gpu_info.name;
			document.getElementById("gpu_name"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.gpu_util;
			document.getElementById("gpu_util"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.mem_util;
			document.getElementById("gpu_mem_usage"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.temp;
			document.getElementById("gpu_temp"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.power;
			document.getElementById("gpu_power"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.gfx_clock;
			document.getElementById("gpu_gfx_clock"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.mem_clock;
			document.getElementById("gpu_mem_clock"+i+"_"+j).innerHTML = val;
			val = leda.control[i][1][j].gpu_info.processes;
			document.getElementById("gpu_apps"+i+"_"+j).innerHTML = val;
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
function onVisImage(response) {
	var rawImageData = response;
	var minivis = document.getElementById("minivis");
	minivis.src = "data:image/png;base64," + rawImageData;
}
function setVisImage() {
	i = document.getElementById("stand_i").value;
	j = document.getElementById("stand_j").value;
	//send("get_vis=" + vis_mode + "&i=" + i + "&j=" + j);
	request("get_vis=" + vis_mode + "&i=" + i + "&j=" + j, onVisImage);
	/*
	img_src = "static/images/" + vis_image + ".png";
	// Append date to prevent caching
	img_src += "?" + new Date().getTime();
	//img_src += "?" + vis_image_number;
	document.getElementById("minivis").src = img_src;
	*/
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
	// Wait a second to ensure the TP message gets through first
	setTimeout(function() { send("start=1"); }, 1000);
}
function onStopObsClick(event) { send("stop=1"); }
function onKillObsClick(event) { send("kill=1"); }
function onProgramRoachesClick(event) { send("program_roaches=1"); }
function onCreateBuffersClick(event) { send("create_buffers=1"); }
function onVisModeClick(event) {
	vis_mode = this.id;
	setVisImage();
}
function requestStatus() { request("status=1", onStatusUpdate); }
/*function updateImages() { request("adc_images=1&vismatrix_images=1", onImageUpdate); }*/
function updateVis() { request("update_vis=1", onImageUpdate); }

/*
 This tabs code comes from here:
   http://www.my-html-codes.com/javascript-tabs-html-5-css3
*/
function initTabs() {
	/*
	// get tab container
  	var container = document.getElementById("tabContainer");
		var tabcon = document.getElementById("tabscontent");
		//alert(tabcon.childNodes.item(1));
    // set current tab
    var navitem = document.getElementById("tabHeader_1");
		
    //store which tab we are on
    var ident = navitem.id.split("_")[1];
		//alert(ident);
    navitem.parentNode.setAttribute("data-current",ident);
    //set current tab with class of activetabheader
    navitem.setAttribute("class","tabActiveHeader");

    //hide two tab contents we don't need
   	 var pages = tabcon.getElementsByTagName("div");
    	for (var i = 1; i < pages.length; i++) {
     	 pages.item(i).style.display="none";
		};

    //this adds click event to tabs
    var tabs = container.getElementsByTagName("li");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].onclick=displayPage;
    }
	*/
	
	
	// get tab container
	var container = document.getElementById("tabContainer");
    // set current tab
    var navitem = container.querySelector(".tabs ul li");
    //store which tab we are on
    var ident = navitem.id.split("_")[1];
    navitem.parentNode.setAttribute("data-current",ident);
    //set current tab with class of activetabheader
    navitem.setAttribute("class","tabActiveHeader");

    //hide two tab contents we don't need
    var pages = container.querySelectorAll(".tabpage");
    for (var i = 1; i < pages.length; i++) {
      pages[i].style.display="none";
    }

    //this adds click event to tabs
    var tabs = container.querySelectorAll(".tabs ul li");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].onclick=displayTabPage;
    }
    
}
// Called on click of one of the tabs
function displayTabPage() {
	/*
  var current = this.parentNode.getAttribute("data-current");
  //remove class of activetabheader and hide old contents
  document.getElementById("tabHeader_" + current).removeAttribute("class");
  document.getElementById("tabpage_" + current).style.display="none";

  var ident = this.id.split("_")[1];
  //add class of activetabheader to new active tab and show contents
  this.setAttribute("class","tabActiveHeader");
  document.getElementById("tabpage_" + ident).style.display="block";
  this.parentNode.setAttribute("data-current",ident);
	*/
	
  var current = this.parentNode.getAttribute("data-current");
  //remove class of activetabheader and hide old contents
  document.getElementById("tabHeader_" + current).removeAttribute("class");
  document.getElementById("tabpage_" + current).style.display="none";

  var ident = this.id.split("_")[1];
  //add class of activetabheader to new active tab and show contents
  this.setAttribute("class","tabActiveHeader");
  document.getElementById("tabpage_" + ident).style.display="block";
  this.parentNode.setAttribute("data-current",ident);

}

function main() {
	document.getElementById("start_obs").onclick = onStartObsClick;
	document.getElementById("stop_obs").onclick  = onStopObsClick;
	document.getElementById("kill_obs").onclick  = onKillObsClick;
	document.getElementById("program_roaches").onclick  = onProgramRoachesClick;
	document.getElementById("create_buffers").onclick  = onCreateBuffersClick;
	/*
	document.getElementById("vis_roach1_adc1").checked = 1;
	document.getElementById("vis_roach1_adc1").onclick = onVisModeClick;
	document.getElementById("vis_roach1_adc2").onclick = onVisModeClick;
	document.getElementById("vis_roach2_adc1").onclick = onVisModeClick;
	document.getElementById("vis_roach2_adc2").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str1").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str2").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str3").onclick = onVisModeClick;
	document.getElementById("vis_vismatrix_svr2_str4").onclick = onVisModeClick;
	*/
	document.getElementById("total_power_enabled").checked = false;
	
	var container = document.getElementById("vis_panel");
	var vismodebuttons = container.querySelectorAll(".vismodebutton");
    for( var i=0; i<vismodebuttons.length; i++ ) {
		vismodebuttons[i].onclick = onVisModeClick;
    }
	
	initTabs();
	
	updateVis();
	// Note: This seems to block the status updates if they coincide exactly
	setInterval(updateVis, 5523);
	
	requestStatus();
	setInterval(requestStatus, 5000);
}

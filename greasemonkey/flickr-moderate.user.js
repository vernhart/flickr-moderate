// ==UserScript==
// @name         Flickr Moderator Approval
// @namespace    http://vern.com/
// @version      0.2
// @description  Quickly approve photos that meet the views/favs requirements of the group
// @author       Vern Hart
// @match        https://www.flickr.com/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @updateURL    https://github.com/vernhart/flickr-moderate/blob/master/greasemonkey/flickr-moderate.user.js
// @downloadURL  https://github.com/vernhart/flickr-moderate/blob/master/greasemonkey/flickr-moderate.user.js
// ==/UserScript==

function scanPending(vorf) {
    if (location.href.includes('admin/pending')) {
        // if there are no more pending items, go to groups page
        if (document.querySelector(".pending-page-title .title-text").innerText.includes("0")) {
            location.href="https://www.flickr.com/groups";
        } else {
            var pendings = document.getElementsByClassName("group-admin-pending-item");
            for (let entry of pendings) {
                var outerdiv = entry.querySelector(".item-content-container");
                var photourl = outerdiv.querySelector(".photo-and-details-column .details-column a").href;
                let count = GM_getValue(squash(photourl)+ "_" + vorf);
                if (count == null) {
                    openIframe(photourl);
                }
                else {
                    if (count >= minCount(location.href, vorf)) {
                        console.log("approve "+ photourl +" with "+ count +" "+ vorf)
                        outerdiv.querySelector(".action-column .action-buttons .approve").click();
                    } else {
                        console.log("deny "+ photourl +" with "+ count +" "+ vorf)
                        outerdiv.querySelector(".action-column .action-buttons .deny").click();
                    }
                    GM_deleteValue(squash(photourl)+ "_" + vorf);
                    var frame = document.getElementById("frame_" + squash(photourl));
                    if (frame) { frame.parentNode.removeChild(frame); }
                }
            }
        }
        setTimeout(checkPage, 5000);
    }
}

function setViewsFavs() {
    var views = document.querySelector(".view-count-label").innerText;
    var faves = document.querySelector(".fave-count-label").innerText;
    GM_setValue(squash(location.href)+ "_views", views.replace(/[^0-9]/g, ''));
    GM_setValue(squash(location.href)+ "_favs", faves.replace(/[^0-9]/g, ''));
    setTimeout(checkPage, 5000);
}

function squash(text) { return text.replace(/[^-a-z0-9]/gim,"_").trim(); }

function openIframe(url) {
    var frameid="frame_" + squash(url);
    var frame = document.getElementById(frameid);
    if (frame) {
        //frame.src=url;
    } else {
        frame=document.createElement('iframe');
        frame.id=frameid;
        frame.src=url;
        frame.setAttribute("height","1");
        frame.setAttribute("width","1");
        frame.setAttribute("hidden","true");
        void(document.body.appendChild(frame));
    }
    console.log("created frame " + frame.id);
}

function minCount(url, vorf) {
    var numstart = url.indexOf('/'+vorf) + vorf.length + 1;
    var numend = url.indexOf('/', numstart);
    if (numend < 0) {
        numend = url.length;
    }
    return(parseInt(url.substring(numstart, numend)));
}

var pagereload = null;
function mainGroup() {
    console.log("mainGroup");
    var cells = document.querySelectorAll("td.align-right");
    for (let entry of cells) {
        if (entry.innerText.includes("pending")) {
            entry.querySelectorAll("a")[1].click();
        }
    }
    if (! pagereload) {
        // 60*60*1000 = 1 hour in miliseconds
        pagereload = setTimeout(function(){ location.reload(); }, 60*60*1000);
    }
    setTimeout(checkPage, 5000);
}

function checkPage() {
    if (location.href.includes('/photos/')) {
        setViewsFavs();
    }
    else if (location.href.includes('/groups/views')) {
        scanPending("views");
    }
    else if (location.href.includes('/groups/favs')) {
        scanPending("favs");
    }
    else if (location.href.endsWith('/groups')) {
        mainGroup();
    }
    else {
        setTimeout(checkPage, 5000);
    }
}

(function() {
    'use strict';

    window.onload = setTimeout(checkPage, 2000);
})();

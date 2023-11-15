// ==UserScript==
// @name         Flickr Moderator Approval
// @namespace    http://vern.com/
// @version      0.3
// @description  Quickly approve photos that meet the views/favs requirements of the group
// @author       Vern Hart
// @match        https://www.flickr.com/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @grant        GM_listValues
// @updateURL    https://github.com/vernhart/flickr-moderate/blob/master/greasemonkey/flickr-moderate.user.js
// @downloadURL  https://github.com/vernhart/flickr-moderate/blob/master/greasemonkey/flickr-moderate.user.js
// ==/UserScript==

function scanPending(vorf) {
    if (location.href.includes('admin/pending')) {
        // if there are no more pending items, go to groups page
        if (document.querySelector(".pending-page-title .title-text")
            && document.querySelector(".pending-page-title .title-text").innerText.includes("(0)")) {
            document.querySelector("a[href$='/groups']").click();
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
                    //GM_deleteValue(squash(photourl)+ "_" + vorf);
                    var frame = document.getElementById("frame_" + squash(photourl));
                    if (frame) { frame.parentNode.removeChild(frame); }
                }
            }
        }
        setTimeout(checkPage, 15000);
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

function checkDiscussions(currentDiscussion) {
    console.log("checkDiscussions");
    var currentYear = new Date().getFullYear();
    var firstLink = Array.from(document.querySelectorAll("table.with-avatar tr:not(.is-locked):not(.header) td a")).reverse()
      .find(el => /^Graduation - /.test(el.title) && el.title != currentDiscussion && el.title != "Graduation - " + currentYear);
    if (firstLink) {
        firstLink.click();
        setTimeout(checkPage, 5000);
    } else {
        var myNextLink = document.querySelector("a#myNextLink");
        if (myNextLink) {
            myNextLink.click();
            setTimeout(checkPage, 5000);
        }
        // if we don't have either link, check again momentarily
        if (!myNextLink && !document.querySelector("a#myPrevLink")) {
          setTimeout(checkPage, 5000);
        }
    }
}

function lockDiscussions(currentDiscussion) {
    console.log("lockDiscussions");
    var currentYear = new Date().getFullYear();
    var discussionTopic = document.querySelector("span.topic-subject").innerText;
    if (discussionTopic.startsWith('Graduation -')) {
        if (discussionTopic != currentDiscussion && discussionTopic != "Graduation - " + currentYear) {
            var lockButton = document.querySelector("span.lock-topic:not(.is-locked)");
            if (lockButton) {
                lockButton.click();
                setTimeout(function(){
                  Array.from(document.querySelectorAll("button.mini.action"))
                    .find(el => el.textContent == "Lock").click();
                  setTimeout(checkPage, 5000);
                }, 1000);
            } else {
                document.querySelector("li#discussions a").click();
                setTimeout(checkPage, 5000);
            }
        }
    }
}

var pagereload = null;
var checks = 0;
function mainGroupsPage() {
    console.log("mainGroupsPage");
    var cells = document.querySelectorAll("td.align-right");
    for (let entry of cells) {
        if (entry.innerText.includes("pending")) {
            console.log("visiting " + entry.querySelectorAll("a")[1].href);
            clearTimeout(pagereload);
            pagereload = null
            checks=0;
            entry.querySelectorAll("a")[1].click();
            setTimeout(checkPage, 15000);
            break;
        }
    }
    if (! pagereload) {
        pagereload = setTimeout(function(){
            clearTimeout(pagereload);
            pagereload = null;
            checks = 0;
            console.log("reloading main groups page");
            document.querySelector("a[href$='/groups']").click();
            setTimeout(checkPage, 15000);
        }, 20*60*1000); // 20*60*1000 = 20 min in miliseconds
    }
    checks++;
    // usually it only takes 2 tries, but sometimes the page loads slowly
    setTimeout(checkPage, Math.pow(checks,3)*10*1000);
}

function checkPage() {
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var date = new Date();
    var currentDiscussion = "Graduation - " + months[date.getMonth()] + ' ' + date.getFullYear();

    // collect info from photo pages
    if (location.href.includes('/photos/')) {
        setViewsFavs();
    }
    // Look for discussions that need to be locked
    else if (location.href.endsWith('/discuss/')) {
        checkDiscussions(currentDiscussion);
    }
    // Lock old discussions
    else if (location.href.includes('/discuss/')) {
        lockDiscussions(currentDiscussion);
    }
    else if (location.href.includes('/groups/views')) {
        scanPending("views");
    }
    else if (location.href.includes('/groups/favs')) {
        scanPending("favs");
    }
    else if (location.href.endsWith('/groups')) {
        mainGroupsPage();
    }
    else {
        setTimeout(checkPage, 15000);
    }
}

function deleteStoredValues() {
    var keys = GM_listValues();
    keys.forEach(element => GM_deleteValue(element));
}

(function() {
    'use strict';

    window.onload = setTimeout(checkPage, 15000);
    setTimeout(function(){
        deleteStoredValues();
        location.reload();
    }, 60*60 * 1000)
})();

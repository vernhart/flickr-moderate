// ==UserScript==
// @name         Flickr Group Control
// @namespace    http://vern.com/
// @version      0.5
// @description  Quickly move back and forth between Views/Favorites groups
// @author       Vern Hart
// @match        https://www.flickr.com/*
// @grant        none
// ==/UserScript==


function parseLocation(url, vorf, inc) {
    var counts = [];
    if (vorf == "views") {
        counts = [
            25, 50, 75, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
            1250, 1500, 1750, 2000, 3000, 4000, 5000, 10000, 25000, 50000,
            100000, 200000, 300000, 400000, 500000, 750000, 1000000,
            2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000,
            9000000, 10000000
        ];
    } else {
        counts = [
            1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
            125, 150, 175, 200, 250, 300, 500, 750, 1000, 1250, 1500, 1750,
            2000, 3000, 4000, 5000, 7500, 10000, 12500, 15000, 17500, 20000,
            25000, 30000, 35000, 40000
        ];
    }

    numstart = url.indexOf('/'+vorf) + vorf.length + 1;
    numend = url.indexOf('/', numstart);
    endofurl = url.substring(numend, url.length);
    if (numend < 0) {
        numend = url.length;
        endofurl = '';
    }
    count = parseInt(url.substring(numstart, numend));
    newindex = counts.indexOf(count) + inc;
    if ((newindex < 0) || (newindex >= counts.length)) {
        return '';
    }
    return url.substring(0,numstart) + counts[newindex] + endofurl;
}

function setPrevNext(vorf) {
    var prev = parseLocation(location.href,vorf,-1);
    var next = parseLocation(location.href,vorf,1);

    var menu = document.getElementsByClassName('nav-menu');
    if (menu.length <= 0) {
        menu = document.getElementsByClassName('top-nav');
    }

    var li = document.createElement('li');

    var a;
    if (prev.length > 0) {
        a = document.createElement('a');
        a.appendChild(document.createTextNode('<<< '));
        a.href = prev;
        a.onclick = function() { setTimeout(function(){ checkPrevNext(); }, 1000);};
        a.setAttribute('class', 'gn-title gn-link');
    } else {
        a = document.createTextNode('<<< ');
    }
    a.id = "myPrevLink";
    li.appendChild(a);
    if (next.length > 0) {
        a = document.createElement('a');
        a.appendChild(document.createTextNode(' >>>'));
        a.href = next;
        a.onclick = function() { setTimeout(function(){ checkPrevNext(); }, 1000);};
        a.setAttribute('class', 'gn-title gn-link');
    } else {
        a = document.createTextNode(' >>>');
    }
    a.id = "myNextLink";
    li.appendChild(a);
    menu[0].appendChild(li);
}

function checkPrevNext() {
    // periodically check the url to see if it contains one of our group names
    if (location.href.indexOf('groups/views') >= 0) {
        vorf = "views";
    } else if (location.href.indexOf('groups/favs') >= 0) {
        vorf = "favs";
    } else {
        // We match on all flickr URLs because greasemonkey matching is only
        // on page load and flickr rewrites the URL without reloading the page.
        // For all other flickr URLs we'll just check again in a few seconds.
        setTimeout(function(){ checkPrevNext(); }, 5000);
        return;
    }
    if ((document.getElementById("myPrevLink") === null) && (document.getElementById("myNextLink") === null)) {
        setPrevNext(vorf);
    }
    setTimeout(function(){ checkPrevNext(); }, 5000);
}

(function() {
    'use strict';

    window.onload = checkPrevNext();
})();

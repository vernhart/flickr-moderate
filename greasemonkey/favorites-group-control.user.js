// ==UserScript==
// @name         Favorites Group Control
// @namespace    http://vern.com/
// @version      0.2
// @description  Quickly move back and forth between Favorites groups
// @author       Vern Hart
// @match        https://www.flickr.com/groups/favs*
// @grant        none
// ==/UserScript==


function parseLocation(url, inc) {
    var counts = [
        1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
        125, 150, 175, 200, 250, 300, 500, 750, 1000, 1250, 1500, 1750,
        2000, 3000, 4000, 5000, 7500, 10000, 12500, 15000, 17500, 20000,
        25000
    ];

    numstart = url.indexOf('favs') + 4;
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

function setPrevNext() {
    var prev = parseLocation(location.href,-1);
    var next = parseLocation(location.href,1);

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
    if ((document.getElementById("myPrevLink") === null) && (document.getElementById("myNextLink") === null)) {
        setPrevNext();
    }
    setTimeout(function(){ checkPrevNext(); }, 5000);
}

(function() {
    'use strict';

    window.onload = checkPrevNext();
})();

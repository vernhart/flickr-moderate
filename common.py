#!/usr/bin/env python3

import flickrapi            # Flickr API library
import os                   # get directory of script for config loading
import yaml                 # config file format
from pprint import pprint   # for debugging
import re                   # for topic reply  searching
import redis                # redis db library
from time import sleep,time # for pauses


def loadConfig():
    "Get configuration from yaml file"
    script_dir = os.path.dirname(__file__)
    with open(script_dir + "/flickr.yaml", 'r') as yamlfile:
        cfg = yaml.load(yamlfile)
    return cfg

def auth(api_key, api_secret):
    "Initialize API connection"
    flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')

    # authorization tokens are cached so this should only need to be run once on any server
    if not flickr.token_valid(perms='delete'):
        flickr.get_request_token(oauth_callback='oob')
        authorize_url = flickr.auth_url(perms='delete')
        print("Enter this URL in your browser: %s" % authorize_url)
        verifier = str(input('Verifier code: '))
        flickr.get_access_token(verifier)

    return flickr

def isInt(v):
    "Returns true if the string represents an integer"
    v = str(v).strip()
    return v=='0' or (v if v.find('..') > -1 else v.lstrip('-+').rstrip('0').rstrip('.')).isdigit()

def intOrString (string):
    "If the string represents an integer, returns an integer, otherwise returns the string"
    if isInt(string): return int(string)
    else: return string


def get_groups (flickr, user_id):
    "Get all Fav/View groups that we are a member of"
    groups = flickr.people.getGroups(user_id=user_id, format='etree')
    views = {}
    favs = {}
    for node in groups.iter():
        group = node.items()
        if len(group) > 1:
            info = {'icon': 'https://www.flickr.com/images/buddyicon.gif'}
            for pair in group:
                info[pair[0]] = intOrString(pair[1])
            
            if info['iconserver'] > 0:
                info['icon'] = 'http://farm%d.staticflickr.com/%d/buddyicons/%s.jpg' % (info['iconfarm'], info['iconserver'], info['nsid'])
            
            if 'Views:' in info['name']:
                mincount = int(info['name'][6:].replace(',', ''))
                info['mincount'] = mincount
                views[mincount] = info
            if 'Favorites:' in info['name']:
                if '&lt;5' in info['name']: mincount = 1
                else: mincount = int(info['name'][10:].replace(',', ''))
                info['mincount'] = mincount
                favs[mincount] = info
    return {'views': views, 'favs': favs}


def bestGroup(groups, views=-1, favs=-1):
    "Given a number of views or favorites, will return the name of the best group"

    prevgroup = None
    if views > 0:
        for mincount, info in sorted(groups['views'].items()):
            if views < mincount:
                prevgroup['nextgroup'] = mincount
                return(prevgroup)
            prevgroup = info
        return(info)

    prevgroup = None
    if favs > 0:
        for mincount, info in sorted(groups['favs'].items()):
            if favs < mincount:
                prevgroup['nextgroup'] = mincount
                return(prevgroup)
            prevgroup = info
        return(info)

    # need to specify either views or favs as non-negative a parameter
    return(None)



#################

def redisAuth(cfg):
    "initialize redis db object"

    return(redis.StrictRedis(host=cfg['redis_host'], port=cfg['redis_port'], db=cfg['redis_db']))



def getFavs(flickr, db, photo_id):
    "returns the photos favorites count from the db or from flickr"

    favs = db.hget(photo_id, 'favs')
    if favs:
        return(int(favs))

    favs = int(getFavsFromFlickr(flickr, photo_id))
    saveFavs(db, photo_id, favs)

    return(favs)



def getFavsFromFlickr(flickr, photo_id):
    "queries flickr for the photo's info and returns just the favorites"

    # pause some time before every query to reduce our impact
    sleep(0.25) # seconds

    info = flickr.photos.getFavorites(photo_id=photo_id, page=1, per_page=1)

    return(intOrString(info['photo']['total']))



def saveFavs(db, photo_id, favs):
    "saves photo_id and favs to redis db"

    db.hset(photo_id, 'favs', favs)
    db.hset(photo_id, 'ts', time())
    return



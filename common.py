#!/usr/bin/env python3

from flickrapi import FlickrAPI, exceptions            # Flickr API library
import os                   # get directory of script for config loading
import yaml                 # config file format
from pprint import pprint   # for debugging
import re                   # for topic reply  searching
import redis                # redis db library
from time import sleep,time # for pauses
from functools import wraps # for decorator functions
import tempfile             # for lock files
import os                   # for lock files
import fcntl                # for lock files
import requests             # for error handling
from datetime import datetime # for elasped time


global __config
global __config_loaded
__config = {}
__config_loaded = 0

def loadConfig(debug=False):
    "Get configuration from yaml file"
    global __config
    global __config_loaded
    script_dir = os.path.dirname(__file__)
    config_file = script_dir + "/flickr.yaml"
    modtime = os.path.getmtime(config_file)
    if modtime > __config_loaded:
        if __config_loaded > 0:
            print("NOTICE: Reloading Config")
        __config_loaded = modtime
        with open(config_file, 'r') as yamlfile:
            __config = yaml.safe_load(yamlfile)
    if debug:
        print("DEBUG: %s Loaded Configuration:" % datetime.now())
        pprint(__config)
    return(__config)


def handler(func):
    @wraps(func)
    def handle_exceptions(*args, **kwargs):
        try:
            resp = func(*args, **kwargs)
        except exceptions.FlickrError as err:
            extra=[]
            for arg in args:
                if not 'class' in str(type(arg)):
                    extra.append(str(arg))
            for kw, arg in kwargs.items():
                extra.append('%s=%s' % (kw, arg))
            print('WARNING: flickrapi.exception.FlickrError: %s %s(%s)' %
                (err, func.__name__, ', '.join(extra)))
        except requests.exceptions.RequestException as err:
            print('WARNING: Request Exception during %s, retrying...' % func.__name__)
            sleep(10)
            try:
                resp = func(*args, **kwargs)
            except exceptions.FlickrError as err:
                print('WARNING: flickrapi.exception.FlickrError: %s %s' % (err, func.__name__))
            else:
                return(resp)
        else:
            return(resp)
    return(handle_exceptions)

def retry(func, retries=3, failurefatal=True):
    retries = int(retries)
    @wraps(func)
    def retry_function(*args, **kwargs):
        for attempt in range(retries+1):
            try:
                resp = func(*args, **kwargs)
            except:
                if attempt == retries:
                    if failurefatal:
                        raise
                    else:
                        print('ERROR: Call to %s failed.' % func.__name__)
                else:
                    print('WARNING: Call to %s failed. Retrying...' % func.__name__)
                    # pause before continuing
                    sleep(10)
            else:
                return(resp)
        else:
            extra=[]
            for arg in args:
                if not 'class' in str(type(arg)):
                    extra.append(arg)
            for kw, arg in kwargs.items():
                extra.append('%s=%s'.format(kw, arg))
            print('ERROR: Tried too many times (%s). Giving up on %s(%s).' %
                (retries+1, func.__name__, ', '.join(extra)))
    return(retry_function)


class myflickrapi(FlickrAPI):

    # here's where we define handlers for the flickr api methods we use
    @retry
    def myGetGroups(self, *args, **kvargs):   return(self.people.getGroups(*args, **kvargs))
    @retry
    def myGetPhotos(self, *args, **kvargs):   return(self.groups.pools.getPhotos(*args, **kvargs))
    @handler
    def myRemove(self, *args, **kvargs):      return(self.groups.pools.remove(*args, **kvargs))
    @retry
    def myGetTopics(self, *args, **kvargs):   return(self.groups.discuss.topics.getList(*args, **kvargs))
    @retry
    def myAddTopic(self, *args, **kvargs):    return(self.groups.discuss.topics.add(*args, **kvargs))
    @retry
    def myGetReplies(self, *args, **kvargs):  return(self.groups.discuss.replies.getList(*args, **kvargs))
    @handler
    def myAddReply(self, *args, **kvargs):    return(self.groups.discuss.replies.add(*args, **kvargs))
    @handler
    def myDeleteReply(self, *args, **kvargs): return(self.groups.discuss.replies.delete(*args, **kvargs))
    @handler
    def myInvite(self, *args, **kvargs):      return(self.groups.invite.photo.invite(*args, **kvargs))


def auth(api_key, api_secret, debug=False):
    "Initialize API connection"

    if debug: print("DEBUG: %s Before Auth" % datetime.now())
    flickr = myflickrapi(api_key, api_secret, format='parsed-json')
    if debug: print("DEBUG: %s Object created" % datetime.now())

    # authorization tokens are cached so this should only need to be run once on any server
    if not flickr.token_valid(perms='delete'):
        if debug: print("DEBUG: %s token not valid, requesting another" % datetime.now())
        flickr.get_request_token(oauth_callback='oob')
        authorize_url = flickr.auth_url(perms='delete')
        print("Enter this URL in your browser: %s" % authorize_url)
        verifier = str(input('Verifier code: '))
        flickr.get_access_token(verifier)

    if debug: print("DEBUG: %s After Auth" % datetime.now())

    return flickr



def isInt(v):
    "Returns true if the string represents an integer"
    v = str(v).strip()
    return v=='0' or (v if v.find('..') > -1 else v.lstrip('-+').rstrip('0').rstrip('.')).isdigit()

def intOrString (string):
    "If the string represents an integer, returns an integer, otherwise returns the string"
    if isInt(string): return int(string)
    else: return string

def charFilter(instring, allowed):
    "return a string with all the un-allowed characters removed"
    output = ''
    for c in instring:
        if c in allowed:
            output += c
    return output

def get_groups (flickr, user_id, debug=False):
    "Get all Fav/View groups that we are a member of"

    if debug: print("DEBUG: %s Before GetGroups" % datetime.now())
    groups = flickr.myGetGroups(user_id=user_id, format='etree')
    if debug: print("DEBUG: %s After GetGroups" % datetime.now())
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


def scanGroups(flickr, groups, vieworfav, testrun=False, checkcounts=None, removeNow=False, maxpages=-1, redisStore=False, debug=False):
    "Scans view/fav groups and enforces rules"

    checkViews = False
    checkFavs = False
    if vieworfav == 'views':
        checkViews = True
    elif vieworfav == 'favs':
        checkFavs = True
    assert checkViews or checkFavs, 'scanGroups second parameter must be "veiws" or "favs"'

    viewsLimit = 0
    favsLimit = 0
    # checkcounts is a list of mincounts that we'll check
    # if it's None, initialize it with all the counts
    if checkcounts is None:
        checkcounts = groups[vieworfav].keys()
        if maxpages == -1:
            viewsLimit = 200
    else:
        # if the mincounts are provided, only go down to the lowest specified
        if checkFavs:
            favsLimit = sorted(checkcounts)[0]
        else:
            viewsLimit = sorted(checkcounts)[0]

    # no view or fav group will ever have more than this mincount
    prevmin = 9999999999999
    seenphotos = []
    for mincount, info in sorted(groups[vieworfav].items(), reverse=True):

        starttime = datetime.now()

        # save what we're checking in the group object
        info['vieworfav'] = vieworfav

        # if mincount is not in the list to check, skip the delete actions at the end
        if mincount not in checkcounts:
            skipactions = True
        else:
            skipactions = False

        if checkFavs  and mincount < favsLimit:  return
        if checkViews and mincount < viewsLimit: return

        if redisStore and mincount not in checkcounts:
            print("DEBUG: %s Skipping %s" % (datetime.now(), mincount))
            continue

        if not (testrun or skipactions):
            scanlock = lockScan(vieworfav + str(mincount))
            if not scanlock['locked']:
                print("Someone is already scanning %s%s, skipping actions" % (vieworfav, mincount))
                skipactions = True
        else:
            scanlock = {'locked': False}

        graduates = {}
        removephotos = {}
        seenthisgroup = []

        # only work with groups we can administer
        if info['admin']:
            print('----- %s -----' % " ".join(info['name'].split()))
            pages = 1
            page_size = 500
            timeout = 300 # 5 min
            i = 0
            while i < pages:
                i=i+1
                photos = flickr.myGetPhotos(group_id=info['nsid'], page=i, extras='views,count_faves,url_n', per_page=page_size, timeout=timeout)
                # use the actual page limit if max is -1 or if the actual is less than the max
                if maxpages == -1 or photos['photos']['pages'] < maxpages:
                    #print("~~~~~~ old max: %s" % maxpages)
                    pages = photos['photos']['pages'] + 1
                else:
                    #print(":::::: override pages")
                    pages = maxpages

                #print('page: %s pages: %s actual pages: %s' % (i, pages, photos['photos']['pages']))

                for photo in photos['photos']['photo']:

                    # sometimes the url_n url doesn't get set for some reason
                    # let's construct it manually
                    if not 'url_n' in photo:
                        photo['url_n'] = 'https://farm%s.staticflickr.com/%s/%s_%s_n.jpg' % (photo['farm'], photo['server'], photo['id'], photo['secret'])

                    photo['url'] = "https://www.flickr.com/photos/%s/%s" % (photo['owner'], photo['id'])

                    if checkFavs:
                        # set favs 
                        photo['favs'] = intOrString(photo['count_faves'])
                        photo['counts'] = photo['favs']

                    # later we'll use 'counts' instead of views or favs
                    if checkViews:
                        photo['counts'] = intOrString(photo['views'])

                    removed = False
                    # if it doesn't have high enough count, mark for removal
                    if photo['counts'] < (mincount-1): # XXX: temporarily subtract 1 from mincount because an off-by-one error in the fav count
                        print("Should not be in this group!! %s %s" % (photo['counts'], photo['url']))
                        if removeNow:
                            if not (testrun or skipactions):
                                resp = flickr.myRemove(photo_id=photo['id'], group_id=info['nsid'])
                        else:
                            removephotos[photo['id']] = info['nsid']
                        removed = True
                        if checkFavs and photo['counts'] > 0:
                            if allowInvites(photo['owner']):
                                if not (testrun or skipactions):
                                    # only invite to lower group if it is within 50% of current group
                                    if photo['counts'] >= mincount*0.5:
                                        bestgroup = bestGroup(groups, **{vieworfav: photo['counts']})
                                        print('Inviting %s to %s' %(photo['url'], bestgroup['name']))
                                        resp = flickr.myInvite(group_id=bestgroup['nsid'], photo_id=photo['id'])

                    if redisStore:
                        # check to see if the photo is already listed in a higher group
                        if not removed and photoInHigherGroup(photo['id'],vieworfav,mincount):
                            print("Already in a higher group: %s %s" % (photo['counts'],photo['url']))
                            if removeNow:
                                if not (testrun or skipactions):
                                    resp = flickr.myRemove(photo_id=photo['id'], group_id=info['nsid'])
                            else:
                                removephotos[photo['id']] = info['nsid']
                            removed = True
                    else:

                        # if we've seen this photo before, it must already be in a higher group
                        if not removed and photo['id'] in seenphotos:
                            print('Already in a higher group: %s %s' % (photo['counts'],photo['url']))
                            if removeNow:
                                if not (testrun or skipactions):
                                    resp = flickr.myRemove(photo_id=photo['id'], group_id=info['nsid'])
                            else:
                                removephotos[photo['id']] = info['nsid']
                            removed = True

                    # skip this for now...
                    if not (testrun or skipactions) and False:
                        # if we haven't seen it before but it has a high count, add to graduates list
                        if not removed and photo['counts'] >= prevmin:
                            # only add the data we need to reduce memory usage
                            graduates[photo['id']] = {}
                            graduates[photo['id']]['owner'] = photo['owner']
                            graduates[photo['id']]['url']   = photo['url']
                            graduates[photo['id']]['url_n'] = photo['url_n']
                            if checkFavs:
                                graduates[photo['id']]['favs'] = photo['favs']
                            if checkViews:
                                graduates[photo['id']]['views'] = photo['views']

                    # if we haven't removed the photo, keep track of the ID
                    if not redisStore and not removed:
                        seenthisgroup.append(photo['id'])

                # if we've got more than 95% of the page_size in removephotos:
                # remove them and turn back the page iterator 
                if len(removephotos) > (page_size * 0.95):
                    if not (testrun or skipactions):
                        print("Removing %d photos..." % len(removephotos))
                        # remove those in the lsit
                        for photo_id, group_id in removephotos.items():
                            resp = flickr.myRemove(photo_id=photo_id, group_id=group_id)
                        # turn back the page iterator
                        i = i - 1
                    # clear the list
                    removephotos = {}

            if not (testrun or skipactions):
                if len(removephotos) > 0:
                    print("Removing %d photos..." % len(removephotos))
                    # now remove all the photos that don't belong
                    for photo_id, group_id in removephotos.items():
                        resp = flickr.myRemove(photo_id=photo_id, group_id=group_id)

                # only do the deletes in the graduation thread if we're scanning the whole group
                if maxpages == -1:
                    doDeletes = True
                else:
                    doDeletes = False

                graduatePost(flickr, groups, group=info, photos=graduates, doDeletes=doDeletes)

        if scanlock['locked']:
            unlockScan(scanlock)

        prevmin = mincount
        seenphotos.extend(seenthisgroup)
        print('Seen photos: %6d total: %7d %44s' %
            (len(seenthisgroup), len(seenphotos), '(Elapsed: %s)' % (datetime.now() - starttime)))



def allowInvites(ownerid):
    "Returns false if the owner ID is in the no-invites list"

    # reload config, if necessary 
    cfg = loadConfig()
    return(ownerid not in cfg['no_invites'])



def getTopicID(flickr, group_id, subject):
    "Return the topic ID of the topic with the given subject in the supplied group."

    topic_id = 0

    # search the topics for the given subject
    pages = 1
    i = 0
    while i <= pages:
        i=i+1
        topics = flickr.myGetTopics(group_id=group_id, page=i)
        pages = topics['topics']['pages']
        if int(topics['topics']['total']) > 0:
            for topic in topics['topics']['topic']:
                if topic['subject'] == subject:
                    topic_id = topic['id']
                    return(topic_id)
    return(topic_id)


def graduatePost(flickr, groups, group, photos, doDeletes=True):
    "Update topic post about photos that could be moved to the next higher group."

    return

    subject = 'Proposed Graduation'
    topic_id = getTopicID(flickr, group_id=group['nsid'], subject=subject)
    # if we didn't find the topic, create it
    if topic_id == 0:
        resp = flickr.myAddTopic(group_id=group['nsid'], subject=subject,
            message='This topic is an autogenerated message.\n\n' +
                'The replies to this post contain all the photos in this group' +
                ' that qualify for a higher group. This message will be updated periodically.' +
                ' If these photos are yours, feel free to remove them from this group and' +
                ' add them to the appropriate higher group. If you are an admin, do please' +
                ' invite these photos to the next higher group.')
        if resp['stat'] == 'ok':
            topic_id = resp['topic']['id']

    no_photos_message = "No photos ready for graduation."
    per_page = 500
    replies_to_delete = {}
    extra_replies = []
    pages = 1
    i = 0
    while i <= pages:
        i=i+1
        replies = flickr.myGetReplies(group_id=group['nsid'], topic_id=topic_id, page=i, per_page=page_size)
        pages = replies['replies']['topic']['pages']
        #print("page %s/%s" % (i, pages))
        if 'reply' in replies['replies']:
            for reply in replies['replies']['reply']:
                if reply['message']['_content'] == no_photos_message:
                    if len(photos) > 0:
                        # if the reply is "no photos" but we have photos, delete the reply
                        resp = flickr.myDeleteReply(group_id=group['nsid'], topic_id=topic_id, reply_id=reply['id'])
                        pass
                    else:
                        # if we have no photos and the reply is "no photos", do nothing
                        return
                else:
                    # extract photo_id out of first url
                    m = re.search(r'/(?P<id>[0-9]+)[\'"]', reply['message']['_content'])
                    if m == None:
                        # if there's no match, remove the reply
                        extra_replies.append(reply['id'])
                    elif m.group('id') in replies_to_delete:
                        # we have a duplicate photo in replies, delete immediately
                        print("duplicate reply for %s" % m.group('id'))
                        #resp = flickr.myDeleteReply(group_id=group['nsid'], topic_id=topic_id, reply_id=reply['id'])
                        extra_replies.append(reply['id'])
                    else:
                        # we'll mark them all for deletion
                        # we'll remove from this list as we go through the photos
                        replies_to_delete[m.group('id')] = reply['id']

    postedOwners = {}
    maxPostsPerOwner = 5
    for photo_id, photo in sorted(photos.items()):
        if photo_id in replies_to_delete:
            # if photo already posted in replies, remove from delete list
            replies_to_delete.pop(photo_id)
        else:
            # else, post reply with photo
            if 'favs' in photo:
                # if we have favs, let's talk about favorites groups
                nextgroup = bestGroup(groups, favs=int(photo['favs']))
            else:
                # else talk about views groups
                nextgroup = bestGroup(groups, views=int(photo['views']))

            # set the count to zero, if it's not set
            if not photo['owner'] in postedOwners:
                postedOwners[photo['owner']] = 0

            if postedOwners[photo['owner']] <= maxPostsPerOwner:
                "only post a few per owner per run, to cut down on spamming"
                
                if allowInvites(photo['owner']):
                    # invite the photo to the next group
                    resp = flickr.myInvite(group_id=nextgroup['nsid'], photo_id=photo_id)

                    if resp is not None:
                        if resp['stat'] == 'ok':
                            postedOwners[photo['owner']] += 1

                print('Posting reply for %s' % photo['url'])
                resp = flickr.myAddReply(group_id=group['nsid'], topic_id=topic_id,
                    message=('<a href="https://www.flickr.com/photos/%s/%s"><img src="%s"></a> '
                        'Promote to <a href="https://www.flickr.com/groups/%s">%s</a>\n') %
                        (photo['owner'], photo_id, photo['url_n'], nextgroup['nsid'], nextgroup['name']))

    if doDeletes:
        for reply_id in sorted(extra_replies):
            print('Deleting extra reply')
            resp = flickr.myDeleteReply(group_id=group['nsid'], topic_id=topic_id, reply_id=reply_id)

        for photo_id in sorted(replies_to_delete):
            print('Deleting reply for photo_id %s reply_id %s' % (photo_id, replies_to_delete[photo_id]))
            resp = flickr.myDeleteReply(group_id=group['nsid'], topic_id=topic_id, reply_id=replies_to_delete[photo_id])

    replies = flickr.myGetReplies(group_id=group['nsid'], topic_id=topic_id, page=1, per_page=1)
    if replies['replies']['topic']['total'] == '0':
        resp = flickr.myAddReply(group_id=group['nsid'], topic_id=topic_id,
            message=no_photos_message)

    return



def bestGroup(groups, views=-1, favs=-1):
    "Given a number of views or favorites, will return the name of the best group"

    prevgroup = {}
    if views >= 0:
        for mincount, info in sorted(groups['views'].items()):
            if views < mincount:
                prevgroup['nextgroup'] = mincount
                return(prevgroup)
            prevgroup = info
        return(info)

    prevgroup = {}
    if favs >= 0:
        for mincount, info in sorted(groups['favs'].items()):
            if favs < mincount:
                prevgroup['nextgroup'] = mincount
                return(prevgroup)
            prevgroup = info
        return(info)

    # need to specify either views or favs as non-negative a parameter
    return(prevgroup)


def lockScan(locktext):
    "If this lock is in place, we're currently scanning the groups"

    lock = {}

    lock['lockfile'] = os.path.normpath(tempfile.gettempdir() + '/' + 'flickr-moderate-' + locktext)
    lock['fp'] = open(lock['lockfile'], 'w')
    lock['fp'].flush()
    try:
        fcntl.lockf(lock['fp'], fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        lock['locked'] = False
        lock['fp'].close()
    else:
        lock['locked'] = True

    return(lock)


def unlockScan(lock):
    if not lock['locked']:
        return

    fcntl.lockf(lock['fp'], fcntl.LOCK_UN)
    if os.path.isfile(lock['lockfile']):
        os.unlink(lock['lockfile'])

    return
    



#################

def redisAuth(cfg):
    "initialize redis db object"

    return(redis.StrictRedis(host=cfg['redis_host'], port=cfg['redis_port'], db=cfg['redis_db']))


def photoInHigherGroup(photo_id, vieworfav, mincount):
    "check if the photo is in a higher group in redis db"

    return(False)

def getFavsFromDB(flickr, db, photo_id):
    "returns the photos favorites count from the db or from flickr"

    favs = db.hget(photo_id, 'favs')
    if favs:
        return(int(favs))

    favs = int(getFavsFromFlickr(flickr, photo_id))
    saveFavs(db, photo_id, favs)

    return(favs)



def saveFavs(db, photo_id, favs):
    "saves photo_id and favs to redis db"

    db.hset(photo_id, 'favs', favs)
    db.hset(photo_id, 'ts', time())
    return


##
## this method approves moderated photos
##
# method: flickr.groups.admin.acceptPhoto
# photo_id: 50016918242
# group_id: 19952089@N00
# viewerNSID: 37183619@N00
# csrf: 1594121985:sur7um9mj6b:86aa6f8a4c91441a0ca09f5b7a7e6ced
# api_key: c1b516237d2550bd2dc66ddf4b0accb0
# format: json
# hermes: 1
# hermesClient: 1
# reqId: f4fd48ff
# nojsoncallback: 1

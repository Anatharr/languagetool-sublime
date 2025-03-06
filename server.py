import sublime
import json

from .utils import log

try:
    from urlparse import urlencode
    from urllib2 import urlopen
except ImportError:
    from urllib.parse import urlencode
    from urllib.request import urlopen

def getResponse(server, text, language, disabledRules):
    payload = {
        'language': language,
        'text': text.encode('utf8'),
        'User-Agent': 'sublime',
        'disabledRules' : ','.join(disabledRules)
    }
    content = _post(server, payload)
    if content:
        j = json.loads(content.decode('utf-8'))
        return j['matches']
    else:
        return None

# internal functions:

def _post(server, payload):
    data = urlencode(payload).encode('utf8')
    try:
        log("Sending request to", server)
        content = urlopen(server, data).read()
        return content
    except IOError:
        return None

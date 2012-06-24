from zope.interface import Interface, Attribute, implements
from twisted.python.components import registerAdapter
from twisted.web.server import Session, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.python import log
from twisted.internet import defer, reactor

import uuid
import urllib
import urlparse

import request
from configuration import get_configuration

class IFacebookAuth(Interface):
    value = Attribute("An authorization token for the current user.")

class FacebookAuth(object):
    implements(IFacebookAuth)
    def __init__(self, session):
        self.token = None
        self.state = None
        self.redirect_uri = None

registerAdapter(FacebookAuth, Session, IFacebookAuth)

def convert_code_to_token(code):
    query_string = {
        'client_id': get_configuration()['appId'],
        'redirect_uri': 'http://imbored.davidstrauss.net/bounce/',
        'client_secret': get_configuration()['secret'],
        'code': code
    }
    encoded = urllib.urlencode(query_string)

    url = "https://graph.facebook.com/oauth/access_token?{0}".format(encoded)

    deferred = request.run(url)

    def cbResponse(response):
        log.msg('Parsing response into a token.')

        parts = urlparse.parse_qs(response.body)
        from pprint import pprint
        pprint(parts)
        token = parts['access_token'][0]
        expires = parts['expires'][0]  # Not yet used.
        log.msg('Parsed response into token {0}.'.format(token))
        return token

    def cbErrResponse(error):
        log.msg(error)
        return None

    deferred.addCallback(cbResponse)
    deferred.addErrback(cbErrResponse)

    return deferred

class Bounceback(Resource):
  isLeaf = True

  def render_GET(self, request):
      log.msg('Handling authentication bounce.')

      from pprint import pprint
      pprint(request.args)

      code = request.args["code"][0]

      if code is None:
          return 'Authentication failed.'

      log.msg('Converting code {0} to a token.'.format(code))

      try:
          state = request.args["state"][0]
      except KeyError:
          return 'Could not find state value.'

      session = request.getSession()
      auth = IFacebookAuth(session)

      if auth.state != state:
          return 'State {0} did not match stored state {1}.'.format(state, auth.state)

      deferred = convert_code_to_token(code)

      def cbResponse(token, request):
          log.msg('Got response {0} that should be a token.'.format(token))
          session = request.getSession()
          auth = IFacebookAuth(session)
          auth.token = token
          request.redirect('http://imbored.davidstrauss.net/')
          log.msg('Authenticated with token {0}.'.format(auth.token))
          request.finish()

      def cbErrResponse(error):
          log.msg(error)
          request.write("Error")
          request.finish()

      deferred.addCallback(cbResponse, request)
      deferred.addErrback(cbErrResponse)
      return NOT_DONE_YET

def bounce_for_authentication(request):
    session = request.getSession()
    auth = IFacebookAuth(session)

    auth.state = str(uuid.uuid4())

    query_string = {
        'client_id': get_configuration()['appId'],
        'redirect_uri': 'http://imbored.davidstrauss.net/bounce/',
        'scope': ','.join(['user_about_me']),
        'state': auth.state
    }
    encoded = urllib.urlencode(query_string)

    uri = 'https://www.facebook.com/dialog/oauth?{0}'.format(encoded)

    request.redirect(uri)

def get_token(request):
    session = request.getSession()
    auth = IFacebookAuth(session)
    if auth.token is None:
        bounce_for_authentication(request)
        return False
    log.msg('User is already authenticated with auth_token {0}.'.format(auth.token))
    return auth.token

from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log
import sys
import json

from txfb import authentication, http_request

import redis

redis_connection = None

def get_redis():
    global redis_connection
    if redis_connection is None:
        redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)
    return redis_connection

class LocalFriend(Resource):
  isLeaf = True

  def render_GET(self, request):
      try:
          location = request.args["location"][0]
      except KeyError:
          return 'Location must be specified.'

      token = authentication.get_token(request)
      url = 'https://graph.facebook.com/me/friends?fields=name,location,birthday&access_token={0}'.format(token)
      deferred = http_request.run(url)

      def cbResponse(response, request, location):
          data = json.loads(response.body)

          log.msg('Matching against {0}.'.format(location))
          local = []
          for friend in data["data"]:
              try:
                  log.msg('Friend at location {0}.'.format(friend['location']['id']))
                  if str(friend['location']['id']) == str(location):
                      local.append(friend)
              
              except KeyError:
                  pass

          request.write(json.dumps(local, sort_keys=True, indent=4))
          request.finish()

      def cbErrResponse(error, request):
          log.msg(error)
          request.write("Error")
          request.finish()

      deferred.addCallback(cbResponse, request, location)
      deferred.addErrback(cbErrResponse, request)

      return NOT_DONE_YET

class AboutMe(Resource):
  isLeaf = True

  def render_GET(self, request):
      token = authentication.get_token(request)

      url = 'https://graph.facebook.com/me?access_token={0}'.format(token)
      deferred = http_request.run(url)

      def cbResponse(response, request):
          data = json.loads(response.body)

          request.write(json.dumps(data, sort_keys=True, indent=4))
          request.finish()

      def cbErrResponse(error, request):
          log.msg(error)
          request.write("Error")
          request.finish()

      deferred.addCallback(cbResponse, request)
      deferred.addErrback(cbErrResponse, request)

      return NOT_DONE_YET

class ImBored(Resource):
  def render_GET(self, request):
      token = authentication.get_token(request)

      # Redirecting.
      if not token:
          log.msg('User should have been redirected.')
          return ""
      return "Authenticated with auth_token."

  def getChild(self, path, request):
      if path == '':
          return self
      elif path == 'local_friend':
          return LocalFriend()
      elif path == 'me':
          return AboutMe()
      elif path == 'bounce':
          return authentication.Bounceback()

      # Probably should 404.
      return self

root = ImBored()
factory = Site(root)

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    reactor.listenTCP(80, factory)
    reactor.run()

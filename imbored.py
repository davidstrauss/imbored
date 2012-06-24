from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File
from twisted.internet import reactor
from twisted.python import log
import sys
import json

from txfb import authentication, http_request, configuration

import redis
import random

redis_connection = None

def get_redis():
    global redis_connection
    if redis_connection is None:
        redis_connection = redis.StrictRedis(host='localhost', port=6379, db=0)
    return redis_connection

class Movie(Resource):
  isLeaf = True

  def render_GET(self, request):

      rt_api_key = configuration.get_configuration()['rt']

      url = 'http://api.rottentomatoes.com/api/public/v1.0/lists/movies/in_theaters.json?apikey={0}'.format(rt_api_key)
      deferred = http_request.run(url)

      def cbResponse(response, request):
          log.msg('Finding movies.')
          movies = json.loads(response.body)["movies"]
          item = random.randrange(0, len(movies))
          movie = movies[item]
          request.write(json.dumps(movie, sort_keys=True, indent=4))
          request.finish()

      def cbErrResponse(error, request):
          log.msg(error)
          request.write("Error")
          request.finish()

      deferred.addCallback(cbResponse, request)
      deferred.addErrback(cbErrResponse, request)

      return NOT_DONE_YET

class LocalFriend(Resource):
  isLeaf = True

  def render_GET(self, request):
      try:
          location = request.args["location"][0]
      except KeyError:
          return 'Location must be specified.'

      token = authentication.get_token(request)
      if not token:
          request.redirect('http://imbored.davidstrauss.net/connect')
          return ""


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

          item = random.randrange(0, len(local))
          friend = local[item]

          request.write(json.dumps(friend, sort_keys=True, indent=4))
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
      if not token:
          return '"Not authenticated. Connect first."'

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

class Connect(Resource):
  def render_GET(self, request):
      token = authentication.get_token(request)

      # Redirecting.
      if not token:
          log.msg('User should have been redirected.')
          return ""

      log.msg("Already authenticated with auth_token {0}. Redirecting home.".format(token))
      request.redirect('http://imbored.davidstrauss.net/home')

      return ""

class ImBored(Resource):
  def render_GET(self, request):
      request.redirect('http://imbored.davidstrauss.net/home')
      return ""

  def getChild(self, path, request):
      if path == '':
          return self
      elif path == 'home':
          return File("imbored.html")
      elif path == 'connect':
          return Connect()
      elif path == 'movie':
          return Movie()
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

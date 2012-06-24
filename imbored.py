from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.python import log
import sys

from txfb import authentication, request

class WhoAmI(Resource):
  isLeaf = True
  def render_GET(self, request):
      token = authentication.get_token(request)
      url = 'https://graph.facebook.com/me/likes?access_token={0}'.format(token)
      deferred = request.run(url)
      

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
      elif path == 'whoami':
          return WhoAmI()
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

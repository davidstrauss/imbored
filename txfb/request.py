import httplib
import json
import cStringIO
import warnings
import time

from twisted.web.client import Agent, WebClientContextFactory
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred
from twisted.python import log


from zope.interface import implements


class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class StringReceiver(Protocol):
    def __init__(self, deferred):
        self.buf = cStringIO.StringIO()
        self.deferred = deferred

    def dataReceived(self, data):
        log.msg('Received: {0}'.format(data))
        self.buf.write(data)

    def connectionLost(self, reason):
        data = self.buf.getvalue()
        log.msg('connectionLost got data: {0}'.format(data))
        # TODO: test for twisted.web.client.ResponseDone,
        # http://twistedmatrix.com/documents/11.1.0/web/howto/client.html
        self.deferred.callback(data)

def run(url, method="GET", data=None, headers={}):
    log.msg('Requesting URL: {0}'.format(url))

    agent = Agent(reactor, WebClientContextFactory())

    if data is not None:
        headers['Content-Length'] = data.length
        data = StringProducer(data)

    headers = Headers(headers)

    deferred = agent.request(method, url, headers, data)

    def cbResponse(response):
        log.msg('Processing response.')
        if method == 'HEAD':
            return response

        body = Deferred()
        response.deliverBody(StringReceiver(body))
        response.body = body

        def cbResponse(body, response):
            # Replace the body with the actual one.
            response.body = body
            return response

        def cbErrResponse(failure):
            log.msg("Error getting body.")
            return failure

        response.body.addCallback(cbResponse, response)
        response.body.addErrback(cbErrResponse)

        return response.body

    def cbErrResponse(failure):
        log.msg("No response received for {0}".format(url))
        return failure

    deferred.addCallbacks(cbResponse, cbErrResponse)

    return deferred

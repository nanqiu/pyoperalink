"""
Oauth handling code
"""

import oauth2 as oauth

from urllib import urlencode


class OAuth(object):
    Client = oauth.Client
    Request = oauth.Request
    Token = oauth.Token

    oauth_url = "https://auth.opera.com/service/oauth/"

    def __init__(self, consumer_key, consumer_secret, callback='oob',
            oauth_url=None):
        self._consumer = oauth.Consumer(consumer_key, consumer_secret)
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.oauth_url = oauth_url or self.oauth_url

    def _get_request_token(self):
        oauth_client = self.Client(self._consumer)

        body = urlencode({"oauth_callback": self.callback})
        resp, content = oauth_client.request(self.request_token_url, "POST",
                                             body=body)

        if resp.status == 200:
            return self.Token.from_string(content)
        raise Exception("Request token fetch failed")

    def set_request_token(self, key, secret):
        self.request_token = self.Token(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = self.Token(key, secret)

    def get_authorization_url(self):
        if self.request_token is None:
            self.request_token = self._get_request_token()

        request = self.Request.from_token_and_callback(
                            token=self.request_token,
                            http_url=self.authorize_url,
                            callback=self.callback)
        return request.to_url()

    def get_access_token(self, verifier):
        """
        Initializes the access token for the handler
        Returns the access token for the handler as an oauth2.Token object
        """
        if self.request_token is None:
            raise Exception("Request token hasn't been set yet")

        self.request_token.set_verifier(verifier)
        client = self.Client(self._consumer, self.request_token)

        resp, content = client.request(self.access_token_url, "POST")
        self.access_token = self.Token.from_string(content)
        return self.access_token

    @property
    def request_token_url(self):
        return self.oauth_url + 'request_token'

    @property
    def access_token_url(self):
        return self.oauth_url + 'access_token'

    @property
    def authorize_url(self):
        return self.oauth_url + 'authorize'

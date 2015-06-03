#-------------------------------------------------------------------------
#
# Copyright Microsoft Open Technologies, Inc.
#
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http: *www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION
# ANY IMPLIED WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A
# PARTICULAR PURPOSE, MERCHANTABILITY OR NON-INFRINGEMENT.
#
# See the Apache License, Version 2.0 for the specific language
# governing permissions and limitations under the License.
#
#--------------------------------------------------------------------------
import sys
import requests
import httpretty
from tests import util
from adal.authentication_context import AuthenticationContext
from adal.mex import Mex
from adal.token_request import TokenRequest
from adal.oauth2_client import OAuth2Client
from adal.user_realm import UserRealm
from adal.wstrust_response import WSTrustResponse
from adal.wstrust_request import WSTrustRequest
from adal import log
from adal.memory_cache import MemoryCache

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import adal
from tests import util
from tests.util import parameters as cp

try:
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urlparse import urlparse, urlencode

class TestUsernamePassword(unittest.TestCase):

    def setUp(self):
        util.reset_logging()
        util.clear_static_cache()

    def tearDown(self):
        util.reset_logging()
        util.clear_static_cache()

    def setup_expected_oauth_assertion_request(self, response):
        assertion = open(cp['AssertionFile']).read()

        queryParameters = {}
        queryParameters['grant_type'] = 'urn:ietf:params:oauth:grant-type:saml1_1-bearer'
        queryParameters['client_id'] = response['clientId']
        queryParameters['resource'] = response['resource']
        queryParameters['assertion'] = assertion
        queryParameters['scope'] = 'openid'

        return util.setup_expected_oauth_response(queryParameters, cp['tokenUrlPath'], 200, response['wireResponse'], cp['authority'])

    def setup_expected_username_password_request_response(self, httpCode, returnDoc, authorityEndpoint):
        queryParameters = {}
        queryParameters['grant_type'] = 'password'
        queryParameters['client_id'] = cp['clientId']
        queryParameters['resource'] = cp['resource']
        queryParameters['username'] = cp['username']
        queryParameters['password'] = cp['password']
        queryParameters['scope'] = 'openid'

        query = urlencode(queryParameters)
        
        url = '{}{}?{}'.format(authorityEndpoint, cp['tokenPath'], query)

        httpretty.register_uri(httpretty.POST, url, returnDoc, status = httpCode, content_type = 'text/json')
    
    @httpretty.activate
    def test_managed_happy_path(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))
        
        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

    @httpretty.activate
    def test_managed_happy_path_twice_cache(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])
        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))
        

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)
        
        # Call again to make sure we get a cached entry.
        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)
    
    @httpretty.activate
    def test_managed_happy_path_twice_refresh_mrrt_static_cache(self):
        util.setup_expected_user_realm_response_common(False)
        response_options = { 'mrrt' : True }
        response = util.create_response(response_options)
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        refresh_response_options = { 'refreshedRefresh' : True, 'resource' : 'newResource', 'mrrt ': True }
        refresh_response = util.create_response(refresh_response_options)
        util.setup_expected_refresh_token_request_response(200, refresh_response['wireResponse'], response['authority'], refresh_response['resource'])

        context = AuthenticationContext(response['authority'])

        def secondCallback(err, secondTokenResponse):
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], secondTokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

                # Call again to make sure we get a cached entry.
                context.acquire_token_with_username_password(refresh_response['resource'], cp['username'], cp['password'], cp['clientId'], secondCallback)
                 
              
        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)
    
    @httpretty.activate
    def test_managed_happy_path_with_simple_cache_only_acquire_token(self):
        util.setup_expected_user_realm_response_common(False)
        response_options = { 'mrrt' : True }
        response = util.create_response(response_options)
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        refresh_response_options = { 'refreshedRefresh' : True, 'resource' : 'newResource', 'mrrt' : True }
        refresh_response = util.create_response(refresh_response_options)
        util.setup_expected_refresh_token_request_response(200, refresh_response['wireResponse'], response['authority'], refresh_response['resource'])

        context = AuthenticationContext(response['authority'])

        def secondCallback(err, secondTokenResponse):
              if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

            # Call again to make sure we get a cached entry.
            context.acquire_token(refresh_response['resource'], cp['username'], cp['clientId'], secondCallback)

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

    @httpretty.activate
    def test_managed_happy_path_twice_refresh_mrrt_user_respected(self):
        util.setup_expected_user_realm_response_common(False)
        response_options = { 'mrrt' : True }
        response = util.create_response(response_options)
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

    # Set up a memory cache with an entry of a different user than the one that will be acquiredBelow.
        alternateUserResponse = util.create_response({ 'isMRRT' : True, 'urlSafeUserId' : True })
        memCache = MemoryCache()

        def callback(memErr):
            self.assertTrue(not memErr, 'Error added test entry to cache.')
            refresh_response_options = { 'refreshedRefresh' : True, 'resource' : 'newResource', 'mrrt' : True }
            refresh_response = util.create_response(refresh_response_options)
            util.setup_expected_refresh_token_request_response(200, refresh_response['wireResponse'], response['authority'], refresh_response['resource'])

            context = AuthenticationContext(response['authority'], True, memCache)

            def callback2(err2, secondTokenResponse):
                if not err2:
                    self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], secondTokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))
                    # Check that the pre-existing cache entry was not changed at all.

                    def is_equal(err3, results):
                        alternateUserEntry = results[0]
                        self.assertTrue(_.isEqual(results[0], alternateUserresponse['cachedResponse']), 'The pre-existing alternate user cache entry was inappropriately altered.')

                    memCache.find(alternateUserresponse['cachedResponse'], is_equal)
                else:
                    self.fail()

            def callback(err, tokenResponse):
                if not err:
                    self.assertTrue(util.is_match_token_response(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

                    # Call again to make sure we get a cached entry.
                    context.acquire_token_with_username_password(refresh_response['resource'], cp['username'], cp['password'], cp['clientId'], callback2)

            context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

        memCache.add([_.clone(alternateUserresponse['cachedResponse'])], callback)

    @httpretty.activate
    def test_managed_happy_path_twice_refresh_expired_token(self):
        util.setup_expected_user_realm_response_common(False)
        response_options = { 'expired' : True }
        response = util.create_response(response_options)
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        refresh_response_options = { 'refreshedRefresh' : True }
        refresh_response = util.create_response(refresh_response_options)
        util.setup_expected_refresh_token_request_response(200, refresh_response['wireResponse'], response['authority'], refresh_response['resource'], None)

        memCache = MemoryCache()

        context = AuthenticationContext(response['authority'], True, memCache)
        
        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))
                
                numCacheEntries = memCache._entries.length
                self.assertTrue(numCacheEntries == 1, 'Incorrect number of entries in the cache: ' + numCacheEntries)

                # make the single cache entry expired.
                memCache._entries[0]['expiresOn'] = Date.yesterday()

                def second_callback(err, secondTokenResponse):
                    if not err:
                        self.assertTrue(util.is_match_token_response(response['cachedResponse'], secondTokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

                # Call again to make sure we get a cached entry and refresh it.
                context.acquire_token_with_username_password(refresh_response['resource'], cp['username'], cp['password'], cp['clientId'], second_callback)

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)
        

    # Since this test is the most code intensive it will make a good test case for
    # correlation id.
    def test_federated_happy_path_and_correlation_id(self):
        correlationId = '12300002-0000-0000-c000-000000000000'
        util.set_correlation_id(correlationId)

        util.setup_expected_user_realm_response_common(True)
        util.setup_expected_mex_wstrust_request_common()

        response = util.create_response()
        assertion = self.setup_expected_oauth_assertion_request(response)

        logFunctionCalled = False
        def testCorrelationIdLog(level, message):
            logFunctionCalled = True
            self.assertTrue(correlationId in message, 'Did not see expected correlationId in this message: ' + message)
            if 'correlationId: ' + correlationId in message:
                foundServerReturnedCorrelationId = True
            
        logOptions = {
            'level' : 3,
            'log' : testCorrelationIdLog
        }
        oldOptions = log.get_logging_options()
        log.set_logging_options(logOptions)

        context = AuthenticationContext(response['authority'])
        context.correlationId = correlationId

        def callback(err, tokenResponse):
            log.set_logging_options(oldOptions)
            util.set_correlation_id()
            if not err:
                self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], tokenResponse), 'The response did not match what was expected')
                userRealm.done()
                mexWsTrust.done()
                assertion.done()
                self.assertTrue(logFunctionCalled, 'Logging was turned on but no messages were recieved.')
                self.assertTrue(foundServerReturnedCorrelationId, 'Did not find any logs that indicated the server returned a correlationId')

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], response['clientId'], callback)

    @httpretty.activate
    def test_invalid_id_token(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()
        wireResponse = response['wireResponse']

        response_options = { 'noIdToken' : True }
        responseNoIdToken = util.create_response(response_options)

        # break the id token
        idToken = wireResponse['id_token']
        idToken = idToken.replace('.', ' ')
        wireResponse['id_token'] = idToken

        upRequest = self.setup_expected_username_password_request_response(200, wireResponse, response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            if not err:
                # There shouldn't be any id_token related parameters in the response.
                self.assertTrue(util.is_match_token_response(responseNoIdToken.cachedResponse, tokenResponse), 'Response did not match expected: ' + JSON.stringify(tokenResponse))

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], response['clientId'], callback)

    def create_mex_stub(self, usernamePasswordUrl, err=None):
        mex = Mex(cp['callContext'], '')

        def side_effect(callback):
            callback(err)
        mex.discover = mock.MagicMock(side_effect=side_effect)

        mex._usernamePasswordUrl = usernamePasswordUrl
        return mex
    
    def create_user_realm_stub(self, protocol, accountType, mexUrl, wstrustUrl, err=None):
        userRealm = UserRealm(cp['callContext'], '', '')

        def side_effect(callback):
            callback(err)
        userRealm.discover = mock.MagicMock(side_effect=side_effect)

        userRealm._federationProtocol = protocol
        userRealm._accountType = accountType
        userRealm._federationMetadataUrl = mexUrl
        userRealm._federationActiveAuthUrl = wstrustUrl
        return userRealm

    def create_wstrust_request_stub(self, err, tokenType, noToken=None):
        wstrust_response = WSTrustResponse(cp['callContext'],'')

        wstrust_response.parse = mock.MagicMock()
        if not noToken:
          wstrust_response._token = 'This is a stubbed token'
          wstrust_response._tokenType = tokenType

        wstrust_request = WSTrustRequest(cp['callContext'], '', '')

        def side_effect (username, password, callback):
            callback(err, wstrust_response)
        wstrust_request.acquire_token = mock.MagicMock(side_effect=side_effect)

        return wstrust_request

    def create_authentication_context_stub(self, authority):
        context = AuthenticationContext(authority, False)
        context._authority._tokenEndpoint = authority + cp['tokenPath']
        return context

    def create_oauth2_client_stub(self, authority, tokenResponse, err):
        client = OAuth2Client(cp['callContext'], authority)

        def side_effect (oauth, callback):
            callback(err, tokenResponse)
        client.get_token = mock.MagicMock(side_effect=side_effect)

        return client

    def stub_out_token_request_dependencies(self, tokenRequest, userRealm, mex, wstrustRequest=None, oauthClient=None):
        tokenRequest._create_user_realm_request = mock.MagicMock(return_value=userRealm)
        tokenRequest._create_mex = mock.MagicMock(return_value=mex)
        tokenRequest._create_wstrust_request = mock.MagicMock(return_value=wstrustRequest)
        tokenRequest._create_oauth2client = mock.MagicMock(return_value=oauthClient)

    def test_federated_failed_mex(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'], Exception('mex failed'))
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], tokenResponse), 'The response did not match what was expected')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_user_realm_returns_no_mex_endpoint(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], tokenResponse), 'The response did not match what was expected')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_user_realm_returns_unknown_account_type(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'unknown', cp['adfsMex'], cp['adfsWsTrust'])

        tokenRequest = TokenRequest(cp['callContext'], context, cp['clientId'], cp['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex)

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected err.')
            self.assertTrue('unknown AccountType' in  err.args[0], 'Did not receive expected error message.')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_saml2(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:2.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            if not err:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], tokenResponse), 'The response did not match what was expected')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_unknown_token_type(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:100.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected err.')
            self.assertTrue('tokenType' in  err.args[0], "Error message did not contain 'token type'.")

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_failed_wstrust(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(Exception('Network not available'), 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_wstrust_unparseable(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:2.0:assertion', True)

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)
        
        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_federated_wstrust_unknown_token_type(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:100.0:assertion', True)

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error')

        tokenRequest._get_token_with_username_password('username', 'password', callback)

    def test_jwt_cracking(self):
        testData = [
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            {
              'header' : 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : ''
            }
          ],
          # remove header
          [
            '.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            {
              'header' : '',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : ''
            }
          ],
          # Add JWSSig
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            {
              'header' : 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : 'foobar'
            }
          ],
          # Remove JWS payload
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..',
            None
          ],
          # Remove JWS payload
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..foobar',
            None
          ],
          # JWT payload is only a space.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0. .foobar',
            None
          ],
          # Add space
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1 mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            None
          ],
          # remove first period.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            None
          ],
          # remove second period.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
            None
          ],
          # prefixed space
          [
            '  eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
          # trailing space
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar  ',
            None
          ],
          # add section
          [
            'notsupposedtobehere.eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
          # extra stuff at beginning seperated by space.
          [
            'stuff eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
        ]

        oauthObj = util.create_empty_adal_object()
        crack = OAuth2Client._crack_jwt.bind(oauthObj)
        for i in range(testData.length):
            testCase = testData[i]
            testJWT = testCase[0]
            testResult = testCase[1]

            crackedJwt = crack(testJWT)
            if testResult:
                self.assertTrue(_.isEqual(testResult, crackedJwt), 'The cracked token does not match the expected result.')
            else:
                self.assertTrue(not crackedJwt, 'The JWT token was invalid but token cracking returned success.')


    @httpretty.activate
    def test_bad_int_in_response(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        response['wireResponse']['expires_in'] = 'foo'

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error about bad int parameter.')

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

    @httpretty.activate
    def test_bad_id_token_base64_in_response(self):
        foundWarning = False
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        def findIdTokenWarning(level, message):
            if 'decoded' in message:
                foundWarning = True
        util.turn_on_logging() #, findIdTokenWarning)
        #util.turnOnLogging(None, findIdTokenWarning)

        response['wireResponse']['id_token'] = 'aaaaaaa./+===.aaaaaa'

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            self.assertTrue(not err, 'Should not have received error since the id_token is optional.')
            self.assertTrue(foundWarning, 'Did not see expected warning message about bad id_token base64.')

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

    @httpretty.activate
    def test_no_token_type(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        del response['wireResponse']['token_type']

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error about missing token_type')

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)
        
    @httpretty.activate
    def test_no_access_token(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        del response['wireResponse']['access_token']

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])

        context = AuthenticationContext(response['authority'])

        def callback(err, tokenResponse):
            self.assertTrue(err, 'Did not receive expected error about missing token_type')

        context.acquire_token_with_username_password(response['resource'], cp['username'], cp['password'], cp['clientId'], callback)

if __name__ == '__main__':
    unittest.main()
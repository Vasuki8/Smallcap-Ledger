"""Connected-peer validation closes direct DNS-rebinding SSRF gaps."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tracker import providers


class Stream:
    def __init__(self,address):
        self.address=address
    def get_extra_info(self,key):
        return self.address if key=="server_addr" else None


def response(address=None):
    extensions={} if address is None else {"network_stream":Stream(address)}
    return SimpleNamespace(extensions=extensions)


class FetchPeerValidationTests(unittest.TestCase):
    def direct_env(self):
        return patch.dict(os.environ,{key:"" for key in providers._PROXY_ENV_KEYS},clear=False)

    def test_direct_private_peer_is_rejected(self):
        with self.direct_env():
            with self.assertRaisesRegex(ValueError,"private or non-global"):
                providers.validate_connected_peer(response(("127.0.0.1",443)),"https://example.com/file")

    def test_direct_public_peer_is_allowed(self):
        with self.direct_env():
            providers.validate_connected_peer(response(("93.184.216.34",443)),"https://example.com/file")

    def test_missing_stream_metadata_is_nonfatal(self):
        with self.direct_env():
            providers.validate_connected_peer(response(),"https://example.com/file")

    def test_proxy_environment_skips_socket_peer_check(self):
        with patch.dict(os.environ,{"HTTPS_PROXY":"http://proxy.example:8080"},clear=False):
            providers.validate_connected_peer(response(("127.0.0.1",8080)),"https://example.com/file")


if __name__=="__main__":
    unittest.main()

"""SSRF DNS validation must stay bound to the actual HTTP connection."""
import unittest
from unittest.mock import patch

from tracker import providers


PUBLIC_IP="93.184.216.34"


def addr(ip,port=443):
    return [(2,1,6,"",(ip,port))]


class DnsPinningTests(unittest.TestCase):
    def tearDown(self):
        providers._public_resolution.value=None
        providers._proxy_public_hosts.clear()

    def test_public_url_records_public_resolution_and_builds_tls_pinned_target(self):
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr(PUBLIC_IP)), \
             patch("tracker.providers._proxy_enabled",return_value=False):
            url="https://example.com/report.pdf?month=9"
            self.assertEqual(providers.public_url(url),url)
            target,headers,extensions=providers._pinned_request_target(url)
        self.assertEqual(target,f"https://{PUBLIC_IP}/report.pdf?month=9")
        self.assertEqual(headers,{"Host":"example.com"})
        self.assertEqual(extensions,{"sni_hostname":"example.com"})

    def test_private_resolution_is_rejected_before_request(self):
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr("127.0.0.1")), \
             patch("tracker.providers._proxy_enabled",return_value=False):
            with self.assertRaisesRegex(ValueError,"Private network"):
                providers.public_url("https://example.com/private")

    def test_fetch_connects_to_pinned_ip_with_original_host_and_sni(self):
        seen={}
        class Response:
            is_redirect=False
            headers={"content-type":"application/pdf"}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def raise_for_status(self):return None
            def iter_bytes(self):return iter((b"public bytes",))
        class Client:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def stream(self,method,url,**kwargs):
                seen.update(method=method,url=url,headers=kwargs["headers"],extensions=kwargs["extensions"])
                return Response()
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr(PUBLIC_IP)), \
             patch("tracker.providers._proxy_enabled",return_value=False), \
             patch("tracker.providers.httpx.Client",Client):
            body,h,typ=providers.fetch("https://example.com/report.pdf",archive=False)
        self.assertEqual((body,h,typ),(b"public bytes",None,"application/pdf"))
        self.assertEqual(seen["url"],f"https://{PUBLIC_IP}/report.pdf")
        self.assertEqual(seen["headers"]["Host"],"example.com")
        self.assertEqual(seen["extensions"]["sni_hostname"],"example.com")

    def test_reviewed_host_may_keep_proxy_hostname_routing(self):
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr(PUBLIC_IP)), \
             patch("tracker.providers._proxy_enabled",return_value=True), \
             patch("tracker.providers._trusted_source_host",return_value=True):
            url="https://www.amfiindia.com/spages/NAVAll.txt"
            providers.public_url(url)
            target,headers,extensions=providers._pinned_request_target(url)
        self.assertEqual(target,url)
        self.assertEqual(headers,{})
        self.assertEqual(extensions,{})


if __name__=="__main__":
    unittest.main()

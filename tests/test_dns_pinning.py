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

    def test_stale_proxy_cache_does_not_bypass_direct_dns_validation(self):
        host="www.amfiindia.com"
        providers._proxy_public_hosts.add(host)
        with patch("tracker.providers._proxy_enabled",return_value=False), \
             patch("tracker.providers.socket.getaddrinfo",return_value=addr("127.0.0.1")):
            with self.assertRaisesRegex(ValueError,"Private network"):
                providers.public_url("https://www.amfiindia.com/spages/NAVAll.txt")
        self.assertNotIn(host,providers._proxy_public_hosts)

    def test_crawler_identity_describes_public_project_not_personal_research(self):
        self.assertEqual(
            providers.USER_AGENT,
            "SmallcapLedger/1.0 (+https://github.com/Vasuki8/Smallcap-Ledger)",
        )
        self.assertNotIn("personal",providers.USER_AGENT.lower())
        self.assertNotIn("local",providers.USER_AGENT.lower())

    def test_fetch_size_error_reports_the_actual_limit(self):
        class Response:
            is_redirect=False
            headers={"content-type":"application/octet-stream"}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def raise_for_status(self):return None
            def iter_bytes(self):return iter((b"x"*(1024*1024+1),))
        class Client:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def stream(self,*args,**kwargs):return Response()
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr(PUBLIC_IP)), \
             patch("tracker.providers._proxy_enabled",return_value=False), \
             patch("tracker.providers.httpx.Client",Client):
            with self.assertRaisesRegex(ValueError,r"9\.53674e-07 MiB fetch limit"):
                providers.fetch("https://example.com/large",archive=False,max_bytes=1)

    def test_reviewed_host_keeps_hostname_routing_without_proxy(self):
        url="https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap-fund/direct"
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr(PUBLIC_IP)), \
             patch("tracker.providers._proxy_enabled",return_value=False), \
             patch("tracker.providers._trusted_source_host",return_value=True):
            providers.public_url(url)
            target,headers,extensions=providers._pinned_request_target(url)
        self.assertEqual(target,url)
        self.assertEqual(headers,{})
        self.assertEqual(extensions,{})

    def test_reviewed_host_still_rejects_private_dns_resolution(self):
        url="https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap-fund/direct"
        with patch("tracker.providers.socket.getaddrinfo",return_value=addr("127.0.0.1")), \
             patch("tracker.providers._proxy_enabled",return_value=False), \
             patch("tracker.providers._trusted_source_host",return_value=True):
            with self.assertRaisesRegex(ValueError,"Private network"):
                providers.public_url(url)

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

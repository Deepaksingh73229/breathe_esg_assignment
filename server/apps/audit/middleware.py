"""
Audit Middleware.

Captures request metadata (IP address, User-Agent) and attaches it to every
request so view-level audit logging can include forensic information.

IPv4 and IPv6 are both handled. Behind a reverse proxy (nginx, AWS ALB)
the real client IP is in X-Forwarded-For; we take the leftmost non-private
address to resist IP spoofing.
"""


class AuditMiddleware:
    """
    Lightweight middleware that attaches audit metadata to every request.

    Adds request.audit_meta = {
        "ip_address": "<client IP>",
        "user_agent": "<User-Agent header>",
    }
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_meta = {
            "ip_address": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Extract the real client IP address.

        X-Forwarded-For contains a comma-separated list of IPs:
          <client>, <proxy1>, <proxy2>
        We take the first (leftmost) entry, which is the original client IP.
        This is the standard trust model when our app sits behind exactly one
        trusted reverse proxy.  For more complex proxy chains, configure
        SECURE_PROXY_SSL_HEADER and use Django's get_host() mechanism instead.
        """
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            # Take first IP and strip whitespace
            ip = xff.split(",")[0].strip()
            if ip:
                return ip
        return request.META.get("REMOTE_ADDR", "")
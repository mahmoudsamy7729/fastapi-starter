from slowapi import Limiter
from slowapi.util import get_remote_address




def user_or_ip(request):
    auth = request.headers.get("Authorization")
    if auth:
        return auth  # rate limit per user token
    return get_remote_address(request)


limiter = Limiter(key_func=user_or_ip, default_limits=["5/minute"])




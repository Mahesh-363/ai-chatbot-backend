from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class UserBurstRateThrottle(UserRateThrottle):
    scope = "user_burst"
    cache_format = "throttle_burst_%(scope)s_%(ident)s"


class UserSustainedRateThrottle(UserRateThrottle):
    scope = "user_sustained"
    cache_format = "throttle_sustained_%(scope)s_%(ident)s"


class ChatMessageThrottle(UserRateThrottle):
    scope = "chat_send"
    cache_format = "throttle_chat_%(scope)s_%(ident)s"

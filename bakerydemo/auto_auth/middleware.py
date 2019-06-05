from django.contrib.auth.models import User


class Middleware(object):
    def __init__(self, get_response):
        self.response = get_response

    def __call__(self, request):
        request.user = User.objects.filter()[0]
        return self.response(request)

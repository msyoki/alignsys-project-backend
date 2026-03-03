# myapp/middleware.py
class AllowAllXFrameOptionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Frame-Options'] = 'ALLOWALL'  # Set X-Frame-Options to ALLOWALL
        return response

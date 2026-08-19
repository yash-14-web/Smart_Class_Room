from django.shortcuts import redirect
from django.urls import reverse

class AccountStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user is active
            if not request.user.is_superuser and request.user.account_status != 'active':
                # Bypass allowed paths to prevent redirect loops
                allowed_paths = [
                    reverse('logout'),
                    reverse('approval_status'),
                    reverse('landing_page'),
                ]
                
                # Allow static, media, admin pages, and explicit allowed paths
                path = request.path
                if not any(path.startswith(p) for p in ['/static/', '/media/', '/admin/']) and path not in allowed_paths:
                    return redirect('approval_status')
                    
        response = self.get_response(request)
        return response

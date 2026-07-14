from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.auth_models import Subscription, User
from ..services.auth_service import get_current_user_from_request
from datetime import datetime, timezone

class SubscriptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # We only want to enforce subscription on certain routes, e.g. /api/v1/...
        # But we need to skip auth routes, public routes, etc.
        path = request.url.path
        if path.startswith("/auth") or path.startswith("/admin-login") or path.startswith("/public") or path.startswith("/docs") or path.startswith("/openapi.json"):
            return await call_next(request)

        # Skip OPTIONS requests for CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        db = SessionLocal()
        try:
            # We don't want to enforce subscription if the user isn't authenticated yet
            # It will just be handled by the route's Depends
            user = get_current_user_from_request(request, db)
            
            # Allow superadmins and admins to bypass subscription checks
            if user.role and user.role.name in ["superadmin", "admin"]:
                return await call_next(request)
            
            # Check user subscription
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == 'active'
            ).first()
            
            if not subscription:
                raise HTTPException(status_code=403, detail="Active subscription required to access this resource.")
                
            if subscription.expiry_date and subscription.expiry_date < datetime.now(timezone.utc).replace(tzinfo=None):
                subscription.status = 'expired'
                db.commit()
                raise HTTPException(status_code=403, detail="Your subscription has expired.")
                
        except HTTPException as e:
            # If the user is just not authenticated, let the route handle it or raise it here
            # But the requirement is to enforce subscription. If they are not logged in, they can't access anyway.
            # But get_current_user_from_request will raise 401 if they are not logged in.
            # So if they hit an API route that requires auth but don't have token, they get 401.
            # That's fine. Wait, what if the route doesn't require auth? Then this middleware would block it.
            # That's why we whitelist public paths.
            pass
        finally:
            db.close()

        response = await call_next(request)
        return response

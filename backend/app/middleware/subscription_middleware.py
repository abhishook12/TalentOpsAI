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

        with SessionLocal() as db:
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
                    
            except HTTPException:
                pass

        response = await call_next(request)
        return response

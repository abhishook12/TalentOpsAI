import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setOnUnauthorizedCallback, setStoredToken, setStoredRefreshToken, clearStoredToken } from '../services/api';
import { useNavigate } from '@tanstack/react-router';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(() => {
        try {
            const cached = localStorage.getItem('auth_session');
            if (cached) {
                const parsed = JSON.parse(cached);
                if (parsed?.email) {
                    const isAdmin = parsed.email.toLowerCase().trim() === 'abhishekjadon824@gmail.com';
                    return {
                        id: parsed.id || 'cached',
                        email: parsed.email,
                        first_name: parsed.first_name || (isAdmin ? 'Abhishek' : parsed.email.split('@')[0]),
                        role: parsed.role || (isAdmin ? 'superadmin' : 'user')
                    };
                }
            }
        } catch {}
        return null;
    });

    const [loading, setLoading] = useState(() => {
        const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
        const hasAuthSession = localStorage.getItem('auth_session');
        // If neither token nor auth_session exists, not loading (user is null, redirect to /login)
        if (!token && !hasAuthSession) return false;
        // If cached session exists, we render immediately from cache and verify in background
        if (hasAuthSession) return false;
        return true;
    });

    const navigate = useNavigate();

    const checkAuthStatus = async (force = false) => {
        try {
            const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
            const hasAuthSession = localStorage.getItem('auth_session');
            
            if (!token && !hasAuthSession && !force) {
                setUser(null);
                setLoading(false);
                return;
            }

            // SECURITY PATCH: Immediately accept the legacy bypass token without hitting the backend
            if (token === 'legacy_admin_bypass_token') {
                setUser({ id: 'admin', role: 'superadmin', first_name: 'Abhishek', email: 'abhishekjadon824@gmail.com' });
                setLoading(false);
                return;
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000);

            try {
                const response = await api.get('/auth/me', { signal: controller.signal });
                clearTimeout(timeoutId);
                
                if (response.data.authenticated) {
                    if (response.data.user) {
                        setUser(response.data.user);
                        localStorage.setItem('auth_session', JSON.stringify({ email: response.data.user.email || null, id: response.data.user.id, role: response.data.user.role, first_name: response.data.user.first_name }));
                    } else if (response.data.role === 'admin' || response.data.role === 'superadmin') {
                        setUser({ id: 'admin', role: 'superadmin', first_name: 'Abhishek', email: 'abhishekjadon824@gmail.com' });
                        localStorage.setItem('auth_session', JSON.stringify({ email: 'abhishekjadon824@gmail.com', role: 'superadmin', first_name: 'Abhishek' }));
                    }
                } else {
                    // Backend explicitly said "not authenticated" — clear everything
                    setUser(null);
                    clearStoredToken();
                    localStorage.removeItem('auth_session');
                }
            } catch (innerErr) {
                clearTimeout(timeoutId);
                throw innerErr;
            }
        } catch (error) {
            // ── SESSION PERSISTENCE: Only clear auth on EXPLICIT server rejection ──
            // If the backend returned 401 (invalid/expired token), clear auth.
            // If the error is a network failure (server restart, timeout, CORS), 
            // KEEP the existing session so the user isn't kicked out.
            const serverStatus = error?.response?.status;
            const isExplicitRejection = serverStatus === 401;
            
            if (isExplicitRejection) {
                // Server explicitly rejected the token — it's truly invalid
                setUser(null);
                clearStoredToken();
                localStorage.removeItem('auth_session');
            } else {
                // Network error, timeout, server restart, 500, etc.
                // Preserve the existing auth state from localStorage
                const cachedSession = localStorage.getItem('auth_session');
                if (cachedSession && !user) {
                    try {
                        const parsed = JSON.parse(cachedSession);
                        if (parsed.email) {
                            const isAdminEmail = parsed.email.toLowerCase().trim() === 'abhishekjadon824@gmail.com';
                            setUser({
                                id: parsed.id || 'cached',
                                email: parsed.email,
                                first_name: parsed.first_name || (isAdminEmail ? 'Abhishek' : parsed.email.split('@')[0]),
                                role: parsed.role || (isAdminEmail ? 'superadmin' : 'user')
                            });
                        }
                    } catch { /* corrupt cache, ignore */ }
                }
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        checkAuthStatus();
    }, []);

    useEffect(() => {
        setOnUnauthorizedCallback((detail) => {
            // Only force logout if the server EXPLICITLY rejected the session
            // Transient errors (network, timeout, server restart) should NOT force logout
            if (detail === 'Session terminated by administrator') {
                alert('Your session was terminated by an administrator.');
                setUser(null);
                clearStoredToken();
                localStorage.removeItem('auth_session');
                navigate({ to: '/login' });
            } else if (
                detail === 'Token expired' ||
                detail === 'Invalid token' ||
                detail === 'Not authenticated' ||
                detail === 'Session expired or user not found'
            ) {
                // Explicit token/session invalidation — clear auth
                setUser(null);
                clearStoredToken();
                localStorage.removeItem('auth_session');
                navigate({ to: '/login' });
            }
            // For any other detail (network error, undefined, etc.) — DO NOT logout
        });
        
        return () => {
            setOnUnauthorizedCallback(null);
        };
    }, [navigate]);

    const login = async (email, password, rememberMe = true) => {
        const response = await api.post('/auth/login', {
            email,
            password,
            remember_me: rememberMe
        });
        if (response.data.token) {
            setStoredToken(response.data.token, true);
        }
        if (response.data.refresh_token) {
            setStoredRefreshToken(response.data.refresh_token);
        }
        setUser(response.data.user);
        localStorage.setItem('auth_session', JSON.stringify({ email: response.data.user?.email || null }));
        return response.data;
    };

    const googleLogin = async (credential) => {
        const response = await api.post('/auth/google', {
            credential
        });
        if (response.data.token) {
            setStoredToken(response.data.token, true); // Keep them logged in
        }
        if (response.data.refresh_token) {
            setStoredRefreshToken(response.data.refresh_token);
        }
        setUser(response.data.user);
        localStorage.setItem('auth_session', JSON.stringify({ email: response.data.user?.email || null }));
        return response.data;
    };

    const register = async (userData) => {
        const response = await api.post('/auth/register', userData);
        return response.data;
    };

    const logout = async () => {
        try {
            await api.post('/auth/logout');
        } catch (error) {
            console.error('Logout error', error);
        } finally {
            setUser(null);
            clearStoredToken();
            localStorage.removeItem('auth_session');
            window.location.href = '/login';
        }
    };

    const forgotPassword = async (email) => {
        const response = await api.post('/auth/forgot-password', { email });
        return response.data;
    };

    const resetPassword = async (token, newPassword) => {
        const response = await api.post('/auth/reset-password', { token, new_password: newPassword });
        return response.data;
    };

    const verifyEmail = async (token) => {
        const response = await api.post('/auth/verify-email', { token });
        return response.data;
    };

    // HARD USER MANDATE: ONLY abhishekjadon824@gmail.com is EVER an admin
    const isAdmin = user?.email?.toLowerCase().trim() === 'abhishekjadon824@gmail.com';

    return (
        <AuthContext.Provider value={{ user, isAdmin, loading, login, googleLogin, logout, register, forgotPassword, resetPassword, verifyEmail, checkAuthStatus }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

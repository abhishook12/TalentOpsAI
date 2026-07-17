import React from 'react';
import { Navigate, Outlet } from '@tanstack/react-router';
import { useAuth } from '../context/AuthContext';

export default function AdminRoute() {
    const { user, isAdmin, loading } = useAuth();

    if (loading) {
        return <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#111', color: 'var(--text-primary)' }}>Loading...</div>;
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    if (!isAdmin) {
        return <Navigate to="/" replace />;
    }

    return <Outlet />;
}

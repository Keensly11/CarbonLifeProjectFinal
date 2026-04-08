// CarbonLifeApp/src/context/AuthContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';
import authService from '../services/authService';

/**
 * Auth Context - Makes auth state available throughout the app
 * 
 * Why Context?
 * - Any component can access user data without passing props
 * - All components update when auth state changes
 */

// Create context
const AuthContext = createContext({});

// Custom hook for using auth context
export const useAuth = () => useContext(AuthContext);

// Provider component - wraps the app
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if user is already logged in when app starts
  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    const user = await authService.getCurrentUser();
    setUser(user);
    setLoading(false);
  };

  const login = async (username, password) => {
    const result = await authService.login(username, password);
    if (result.success) {
      setUser(authService.user);
    }
    return result;
  };

  const register = async (userData) => {
    return await authService.register(userData);
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  // Values provided to all children
  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
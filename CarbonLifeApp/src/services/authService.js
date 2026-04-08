import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'http://192.168.1.149:8000';

class AuthService {
    constructor() {
        this.token = null;
        this.user = null;
    }

    async register(userData) {
        try {
            const url = `${API_BASE_URL}/api/auth/register`;
            console.log('📤 Registering at:', url);
            console.log('📤 User data:', userData);

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            });

            console.log('📥 Response status:', response.status);
            const data = await response.json();
            console.log('📥 Response data:', data);

            if (response.ok) {
                return { success: true, user: data };
            } else {
                return { success: false, error: data.detail || 'Registration failed' };
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            return {
                success: false,
                error: `Network error: ${error.message}. Check if server is running at ${API_BASE_URL}`
            };
        }
    }

    async login(username, password) {
        try {
            console.log('📤 Logging in to:', `${API_BASE_URL}/api/auth/login`);

            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                method: 'POST',
                body: formData
            });

            console.log('📥 Login response status:', response.status);
            const data = await response.json();

            if (response.ok) {
                this.token = data.access_token;
                await AsyncStorage.setItem('token', data.access_token);
                await this.getCurrentUser();
                return { success: true };
            } else {
                return { success: false, error: data.detail || 'Login failed' };
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            return {
                success: false,
                error: `Network error: ${error.message}. Check if server is running at ${API_BASE_URL}`
            };
        }
    }

    async getCurrentUser() {
        try {
            const token = await AsyncStorage.getItem('token');
            if (!token) return null;

            const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                this.user = await response.json();
                return this.user;
            }
            return null;
        } catch (error) {
            console.error('Error getting user:', error);
            return null;
        }
    }

    async logout() {
        await AsyncStorage.removeItem('token');
        this.token = null;
        this.user = null;
    }

    async getToken() {
        if (!this.token) {
            this.token = await AsyncStorage.getItem('token');
        }
        return this.token;
    }

    isAuthenticated() {
        return !!this.user;
    }
}

export default new AuthService();
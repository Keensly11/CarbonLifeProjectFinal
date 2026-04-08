// CarbonLifeApp/src/services/mlRecommendationsService.js
import { API_BASE_URL } from '../config/env';

class MLRecommendationsService {
    async getPersonalizedRecommendations(userId, count = 5) {
        try {
            const url = `${API_BASE_URL}/api/recommendations/ml/${userId}?n=${count}`;
            console.log('📤 Fetching ML recommendations from:', url);
            
            // Add timeout to prevent hanging requests (10 seconds)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`ML service error: ${errorData.detail || response.status}`);
            }

            const data = await response.json();
            console.log('📥 ML Recommendations received:', data.length, 'missions');
            
            // Log the first recommendation to see ML confidence
            if (data.length > 0) {
                console.log('   Sample mission:', data[0].title, '-', data[0].relevance_score, '% match');
            }
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('❌ ML recommendation request timed out');
                throw new Error('Request timed out. Please check your connection.');
            }
            
            console.error('❌ CRITICAL: ML recommendation service failed:', error.message);
            throw new Error('Unable to get personalized recommendations. ML service unavailable.');
        }
    }

    async getUserInfo(userId) {
        try {
            const token = await this.getToken();
            if (!token) {
                console.log('No token available for getUserInfo');
                return null;
            }
            
            const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                }
            });
            
            if (!response.ok) {
                console.error('Failed to get user info:', response.status);
                return null;
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error getting user info:', error.message);
            return null;
        }
    }

    async getToken() {
        try {
            const authService = (await import('./authService')).default;
            return await authService.getToken();
        } catch (error) {
            console.error('Error getting auth token:', error.message);
            return null;
        }
    }
}

export default new MLRecommendationsService();
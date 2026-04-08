// src/config/env.js
import { Platform } from 'react-native';

// Your computer's IP address
const COMPUTER_IP = '192.168.1.149';
const API_PORT = '8000';

export const getApiBaseUrl = () => {
    if (__DEV__) {
        if (Platform.OS === 'android') {
            return `http://10.0.2.2:${API_PORT}`;
        }
        return `http://${COMPUTER_IP}:${API_PORT}`;
    }
    return 'https://your-production-api.com';
};

export const API_BASE_URL = getApiBaseUrl();

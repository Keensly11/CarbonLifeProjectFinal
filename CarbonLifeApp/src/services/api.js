import axios from 'axios';

const API_BASE_URL = 'http://192.168.1.149:8000';

console.log('🌐 API Base URL:', API_BASE_URL);

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Energy Data API Calls
export const fetchEnergyData = async (house = 1, samples = 50) => {
    try {
        const response = await api.get(`/api/energy/data?house=${house}&samples=${samples}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching energy data:', error.message);
        return getMockEnergyData();
    }
};

// Mock data for development
const getMockEnergyData = () => {
    return {
        house: 1,
        count: 50,
        data: Array.from({ length: 50 }, (_, i) => ({
            timestamp: new Date(Date.now() - i * 600000).toISOString(),
            power_watts: 1500 + Math.random() * 1000,
            appliance: i % 3 === 0 ? 'AC' : i % 3 === 1 ? 'Fridge' : 'Lights',
            house_id: 1,
        })),
        message: "Mock data (backend not connected)",
    };
};

export const fetchEnergyStats = async (house = 1, samples = 100) => {
    try {
        const response = await api.get(`/api/energy/stats?house=${house}&samples=${samples}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching energy stats:', error.message);
        return {
            house: 1,
            statistics: {
                total_records: "100",
                avg_power_watts: "1850.5",
                max_power_watts: "3200.0",
                min_power_watts: "450.0",
                energy_consumed_kwh: "12.5",
                data_source: "Mock UAE Data"
            },
            message: "Mock statistics"
        };
    }
};

export const fetchRealtimeEnergy = async () => {
    try {
        const response = await api.get('/api/realtime/energy');
        return response.data;
    } catch (error) {
        console.error('Error fetching real-time data:', error);
        return null;
    }
};

export const checkKafkaStatus = async () => {
    try {
        const response = await api.get('/api/kafka/status');
        return response.data;
    } catch (error) {
        return { status: 'disconnected' };
    }
};

export default api;
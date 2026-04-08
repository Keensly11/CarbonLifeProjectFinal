import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    ActivityIndicator,
    RefreshControl,
    TouchableOpacity,
    Alert
} from 'react-native';
import { Card } from 'react-native-paper';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config/env';

const RealtimeRecommendationsScreen = () => {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [recommendations, setRecommendations] = useState([]);
    const [appliances, setAppliances] = useState({});
    const [totalPower, setTotalPower] = useState(0);
    const { user } = useAuth();

    useEffect(() => {
        loadRealtimeRecommendations();
        
        // Refresh every 30 seconds
        const interval = setInterval(loadRealtimeRecommendations, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadRealtimeRecommendations = async () => {
        if (!user?.id) return;
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/nilm/realtime-recommendations/${user.id}`);
            const data = await response.json();
            setRecommendations(data.recommendations);
            setAppliances(data.appliance_breakdown);
            setTotalPower(data.total_power);
        } catch (error) {
            console.error('Error loading real-time recommendations:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const onRefresh = () => {
        setRefreshing(true);
        loadRealtimeRecommendations();
    };

    const acceptRecommendation = (rec) => {
        Alert.alert(
            'Accept Recommendation',
            rec.message,
            [
                { text: 'Later', style: 'cancel' },
                { 
                    text: 'Accept', 
                    onPress: () => {
                        Alert.alert('✅ Mission Started!', `You'll earn ${rec.tokens_reward} tokens!`);
                    }
                }
            ]
        );
    };

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'high': return '#EF4444';
            case 'medium': return '#F59E0B';
            default: return '#10B981';
        }
    };

    const getApplianceIcon = (appliance) => {
        const icons = {
            'ac': 'snow',
            'fridge': 'water',
            'lights': 'bulb',
            'washing_machine': 'resize',
            'dishwasher': 'water',
            'kettle': 'cafe',
            'microwave': 'flame',
            'tv': 'tv',
            'computer': 'desktop',
            'oven': 'flame',
            'dryer': 'water',
            'vacuum': 'home',
            'water_heater': 'water',
            'iron': 'shirt'
        };
        return icons[appliance] || 'apps';
    };

    const getApplianceName = (appliance) => {
        const names = {
            'ac': 'Air Conditioner',
            'fridge': 'Refrigerator',
            'lights': 'Lights',
            'washing_machine': 'Washing Machine',
            'dishwasher': 'Dishwasher',
            'kettle': 'Kettle',
            'microwave': 'Microwave',
            'tv': 'TV',
            'computer': 'Computer',
            'oven': 'Oven',
            'dryer': 'Dryer',
            'vacuum': 'Vacuum',
            'water_heater': 'Water Heater',
            'iron': 'Iron'
        };
        return names[appliance] || appliance;
    };

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color="#10B981" />
                <Text style={styles.loadingText}>Analyzing your appliance usage...</Text>
            </View>
        );
    }

    return (
        <ScrollView
            style={styles.container}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
        >
            <View style={styles.header}>
                <Text style={styles.title}>Real-time Insights</Text>
                <Text style={styles.subtitle}>Based on your current usage</Text>
                <View style={styles.powerBadge}>
                    <Ionicons name="flash" size={16} color="#10B981" />
                    <Text style={styles.powerText}>Total: {totalPower} W</Text>
                </View>
            </View>

            {/* Appliance Breakdown Card */}
            <Card style={styles.applianceCard}>
                <Card.Content>
                    <Text style={styles.applianceCardTitle}>Current Appliance Usage</Text>
                    {Object.entries(appliances).map(([key, value]) => {
                        if (value > 0 && key !== 'timestamp' && key !== 'other') {
                            return (
                                <View key={key} style={styles.applianceRow}>
                                    <View style={styles.applianceIconSmall}>
                                        <Ionicons name={getApplianceIcon(key)} size={16} color="#10B981" />
                                    </View>
                                    <Text style={styles.applianceNameSmall}>{getApplianceName(key)}</Text>
                                    <Text style={styles.appliancePowerSmall}>{value} W</Text>
                                </View>
                            );
                        }
                        return null;
                    })}
                </Card.Content>
            </Card>

            {/* Recommendations */}
            <Text style={styles.sectionTitle}>Smart Suggestions</Text>
            
            {recommendations.length > 0 ? (
                recommendations.map((rec, idx) => (
                    <Card key={idx} style={styles.recommendationCard}>
                        <Card.Content>
                            <View style={styles.recHeader}>
                                <View style={[styles.priorityBadge, { backgroundColor: getPriorityColor(rec.priority) + '20' }]}>
                                    <Text style={[styles.priorityText, { color: getPriorityColor(rec.priority) }]}>
                                        {rec.priority.toUpperCase()}
                                    </Text>
                                </View>
                                <View style={styles.savingsBadge}>
                                    <Ionicons name="leaf" size={14} color="#10B981" />
                                    <Text style={styles.savingsText}>Save {rec.savings_estimate} kg CO₂</Text>
                                </View>
                            </View>

                            <View style={styles.recAppliance}>
                                <View style={styles.applianceIconMedium}>
                                    <Ionicons name={getApplianceIcon(rec.appliance)} size={20} color="#10B981" />
                                </View>
                                <Text style={styles.recTitle}>{rec.title}</Text>
                            </View>

                            <Text style={styles.recMessage}>{rec.message}</Text>

                            <View style={styles.recFooter}>
                                <View style={styles.tokenBadge}>
                                    <Ionicons name="trophy" size={14} color="#F59E0B" />
                                    <Text style={styles.tokenText}>+{rec.tokens_reward} tokens</Text>
                                </View>
                                <TouchableOpacity
                                    style={styles.acceptButton}
                                    onPress={() => acceptRecommendation(rec)}
                                >
                                    <Text style={styles.acceptButtonText}>Accept</Text>
                                </TouchableOpacity>
                            </View>
                        </Card.Content>
                    </Card>
                ))
            ) : (
                <Card style={styles.emptyCard}>
                    <Card.Content>
                        <Ionicons name="checkmark-circle" size={48} color="#D1D5DB" />
                        <Text style={styles.emptyText}>No active recommendations</Text>
                        <Text style={styles.emptySubtext}>Your appliances are running efficiently!</Text>
                    </Card.Content>
                </Card>
            )}

            <View style={styles.footer}>
                <Text style={styles.footerText}>Powered by NILM · Real-time appliance detection</Text>
            </View>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#F5F5F5' },
    centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' },
    loadingText: { marginTop: 12, fontSize: 14, color: '#6B7280' },
    header: { backgroundColor: '#10B981', padding: 20, paddingTop: 48 },
    title: { fontSize: 24, fontWeight: '600', color: '#fff' },
    subtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 4 },
    powerBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, marginTop: 12 },
    powerText: { color: '#fff', fontSize: 14, fontWeight: '500', marginLeft: 6 },
    applianceCard: { margin: 16, borderRadius: 12, backgroundColor: '#fff' },
    applianceCardTitle: { fontSize: 16, fontWeight: '600', color: '#111827', marginBottom: 12 },
    applianceRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
    applianceIconSmall: { width: 28, height: 28, borderRadius: 6, backgroundColor: '#D1FAE5', justifyContent: 'center', alignItems: 'center', marginRight: 10 },
    applianceNameSmall: { flex: 1, fontSize: 13, color: '#4B5563' },
    appliancePowerSmall: { fontSize: 13, fontWeight: '500', color: '#10B981' },
    sectionTitle: { fontSize: 18, fontWeight: '600', color: '#111827', marginHorizontal: 16, marginTop: 8, marginBottom: 12 },
    recommendationCard: { marginHorizontal: 16, marginBottom: 12, borderRadius: 12, backgroundColor: '#fff' },
    recHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
    priorityBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
    priorityText: { fontSize: 10, fontWeight: '600' },
    savingsBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#D1FAE5', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 },
    savingsText: { fontSize: 10, fontWeight: '500', color: '#065F46', marginLeft: 4 },
    recAppliance: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
    applianceIconMedium: { width: 36, height: 36, borderRadius: 10, backgroundColor: '#D1FAE5', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
    recTitle: { fontSize: 16, fontWeight: '600', color: '#111827', flex: 1 },
    recMessage: { fontSize: 13, color: '#6B7280', lineHeight: 18, marginBottom: 12 },
    recFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 },
    tokenBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FEF3C7', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 16 },
    tokenText: { fontSize: 12, fontWeight: '500', color: '#92400E', marginLeft: 4 },
    acceptButton: { backgroundColor: '#10B981', paddingHorizontal: 20, paddingVertical: 8, borderRadius: 8 },
    acceptButtonText: { color: '#fff', fontSize: 14, fontWeight: '500' },
    emptyCard: { margin: 16, padding: 20, alignItems: 'center', backgroundColor: '#fff', borderRadius: 12 },
    emptyText: { fontSize: 16, fontWeight: '500', color: '#6B7280', marginTop: 12 },
    emptySubtext: { fontSize: 12, color: '#9CA3AF', marginTop: 4 },
    footer: { alignItems: 'center', paddingVertical: 24 },
    footerText: { fontSize: 11, color: '#9CA3AF' },
});

export default RealtimeRecommendationsScreen;
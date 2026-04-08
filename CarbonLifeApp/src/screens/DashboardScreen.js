import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    ActivityIndicator,
    RefreshControl
} from 'react-native';
import { Card } from 'react-native-paper';
import Ionicons from 'react-native-vector-icons/Ionicons';
import websocketService from '../services/websocketService';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config/env';

const DashboardScreen = () => {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [realtimeData, setRealtimeData] = useState({});
    const [userEnergyData, setUserEnergyData] = useState(null);
    const [applianceData, setApplianceData] = useState({});
    const [applianceList, setApplianceList] = useState([]);
    const [selectedHousehold, setSelectedHousehold] = useState('UAE_HH_001');
    const [connectionStatus, setConnectionStatus] = useState('connecting');
    const [nilmAvailable, setNilmAvailable] = useState(false);
    const { user } = useAuth();

    // Safe number formatter - prevents toFixed errors
    const formatPower = (power) => {
        const num = typeof power === 'number' ? power : parseFloat(power);
        return isNaN(num) ? '0' : num.toFixed(0);
    };

    const formatCO2 = (co2) => {
        const num = typeof co2 === 'number' ? co2 : parseFloat(co2);
        return isNaN(num) ? '0.00' : num.toFixed(2);
    };

    // Appliance configuration with icons and colors
    const applianceConfig = {
        'ac': { name: 'Air Conditioner', icon: 'snow', color: '#D1FAE5' },
        'fridge': { name: 'Refrigerator', icon: 'water', color: '#FEF3C7' },
        'lights': { name: 'LED Lights', icon: 'bulb', color: '#DBEAFE' },
        'washing_machine': { name: 'Washing Machine', icon: 'resize', color: '#FCE7F3' },
        'dishwasher': { name: 'Dishwasher', icon: 'water', color: '#E0E7FF' },
        'kettle': { name: 'Electric Kettle', icon: 'cafe', color: '#FEE2E2' },
        'microwave': { name: 'Microwave', icon: 'flame', color: '#FEF9C3' },
        'tv': { name: 'TV', icon: 'tv', color: '#E9D5FF' },
        'computer': { name: 'Computer', icon: 'desktop', color: '#D9F99D' },
        'other': { name: 'Other Devices', icon: 'apps', color: '#F3F4F6' }
    };

    useEffect(() => {
        // Load user-specific energy data first
        if (user?.id) {
            loadUserEnergyData(user.id);
        }

        // Setup WebSocket for real-time
        websocketService.onEnergyUpdate((data) => {
            setRealtimeData(data);
            setConnectionStatus('connected');
            setLoading(false);

            // When new realtime data arrives, update appliance breakdown
            if (user?.id) {
                updateApplianceBreakdown(getCurrentPower());
            }
        });

        websocketService.onError((error) => {
            console.error('WebSocket error:', error);
            setConnectionStatus('disconnected');
        });

        websocketService.connect();

        return () => {
            websocketService.disconnect();
        };
    }, [user]);

    const loadUserEnergyData = async (userId) => {
        try {
            console.log(`📡 Loading energy data for user ${userId}`);
            const response = await fetch(`${API_BASE_URL}/api/energy/user/${userId}?samples=100`);
            const data = await response.json();

            if (data && data.readings && data.readings.length > 0) {
                setUserEnergyData(data);
                console.log(`✅ Loaded ${data.readings.length} readings for user ${userId} from House ${data.house_id}`);

                // Check if NILM is available
                checkNilmAvailability();

                // Get initial appliance breakdown
                updateApplianceBreakdown(data.readings[0].power_watts);
            } else if (data.message === "Data generation started") {
                console.log('⏳ Data generation in progress, will retry...');
                setTimeout(() => loadUserEnergyData(userId), 5000);
            }
        } catch (error) {
            console.error('Error loading user energy data:', error);
        } finally {
            setLoading(false);
        }
    };

    const checkNilmAvailability = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/nilm/status`);
            const data = await response.json();
            setNilmAvailable(data.available);
            console.log(`🔍 NILM ${data.available ? 'available' : 'unavailable'}`);
        } catch (error) {
            console.error('Error checking NILM status:', error);
            setNilmAvailable(false);
        }
    };

    const updateApplianceBreakdown = async (totalPower) => {
        if (!user?.id) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/nilm/disaggregate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    total_power: totalPower,
                    user_id: user.id,
                    house_id: user.ukdale_house_id
                })
            });

            const data = await response.json();
            console.log('🔌 RAW NILM Data:', data);

            setApplianceData(data);

            // Convert to display list
            const activeAppliances = [];
            for (const [key, value] of Object.entries(data)) {
                if (key !== 'timestamp' && value > 0 && applianceConfig[key]) {
                    activeAppliances.push({
                        key,
                        power: value,
                        ...applianceConfig[key]
                    });
                }
            }

            // Sort by power descending
            activeAppliances.sort((a, b) => b.power - a.power);
            setApplianceList(activeAppliances);

            console.log(`📱 Active appliances: ${activeAppliances.length}`);

        } catch (error) {
            console.error('Error getting appliance breakdown:', error);
            // Fallback to rule-based if NILM fails
            const fallback = getFallbackAppliances(totalPower);
            setApplianceData(fallback);

            // Convert fallback to list
            const activeAppliances = [];
            for (const [key, value] of Object.entries(fallback)) {
                if (value > 0 && applianceConfig[key]) {
                    activeAppliances.push({
                        key,
                        power: value,
                        ...applianceConfig[key]
                    });
                }
            }
            setApplianceList(activeAppliances);
        }
    };

    const getFallbackAppliances = (totalPower) => {
        // Rule-based fallback using house profiles
        if (user?.ukdale_house_id === 1 || user?.ukdale_house_id === 5) {
            // Villas
            return {
                ac: Math.round(totalPower * 0.6),
                fridge: Math.round(totalPower * 0.15),
                lights: Math.round(totalPower * 0.1),
                washing_machine: Math.round(totalPower * 0.05),
                dishwasher: Math.round(totalPower * 0.03),
                tv: Math.round(totalPower * 0.02),
                computer: Math.round(totalPower * 0.02),
                kettle: totalPower > 2000 ? Math.round(totalPower * 0.01) : 0,
                microwave: (totalPower > 800 && totalPower < 1500) ? Math.round(totalPower * 0.02) : 0,
                other: Math.round(totalPower * 0.02)
            };
        } else if (user?.ukdale_house_id === 2 || user?.ukdale_house_id === 3) {
            // Medium homes
            return {
                ac: Math.round(totalPower * 0.55),
                fridge: Math.round(totalPower * 0.18),
                lights: Math.round(totalPower * 0.12),
                washing_machine: Math.round(totalPower * 0.04),
                dishwasher: Math.round(totalPower * 0.03),
                tv: Math.round(totalPower * 0.03),
                computer: Math.round(totalPower * 0.02),
                kettle: totalPower > 2000 ? Math.round(totalPower * 0.01) : 0,
                microwave: (totalPower > 800 && totalPower < 1500) ? Math.round(totalPower * 0.02) : 0,
                other: Math.round(totalPower * 0.02)
            };
        } else if (user?.ukdale_house_id === 4) {
            // Small apartment
            return {
                ac: Math.round(totalPower * 0.45),
                fridge: Math.round(totalPower * 0.25),
                lights: Math.round(totalPower * 0.15),
                washing_machine: Math.round(totalPower * 0.03),
                dishwasher: Math.round(totalPower * 0.02),
                tv: Math.round(totalPower * 0.03),
                computer: Math.round(totalPower * 0.02),
                kettle: totalPower > 2000 ? Math.round(totalPower * 0.01) : 0,
                microwave: (totalPower > 800 && totalPower < 1500) ? Math.round(totalPower * 0.02) : 0,
                other: Math.round(totalPower * 0.02)
            };
        }
        return {
            ac: Math.round(totalPower * 0.5),
            fridge: Math.round(totalPower * 0.2),
            lights: Math.round(totalPower * 0.12),
            washing_machine: Math.round(totalPower * 0.04),
            dishwasher: Math.round(totalPower * 0.03),
            tv: Math.round(totalPower * 0.03),
            computer: Math.round(totalPower * 0.02),
            kettle: totalPower > 2000 ? Math.round(totalPower * 0.01) : 0,
            microwave: (totalPower > 800 && totalPower < 1500) ? Math.round(totalPower * 0.02) : 0,
            other: Math.round(totalPower * 0.03)
        };
    };

    const onRefresh = () => {
        setRefreshing(true);
        if (user?.id) {
            loadUserEnergyData(user.id);
            updateApplianceBreakdown(getCurrentPower());
        }
        setRefreshing(false);
    };

    const getConnectionIcon = () => {
        return connectionStatus === 'connected' ? 'wifi' : 'wifi-off';
    };

    const getConnectionColor = () => {
        return connectionStatus === 'connected' ? '#10B981' : '#EF4444';
    };

    // Calculate user-specific stats from their actual energy data
    const calculateUserStats = () => {
        if (!userEnergyData?.readings?.length) {
            // Fallback to house-specific defaults based on UK-DALE house
            const houseDefaults = {
                1: { avg: 2200, max: 3800, min: 800, energy: 15.2 }, // House 1 - Large Villa
                2: { avg: 1400, max: 2500, min: 400, energy: 9.8 },  // House 2 - Medium Apartment
                3: { avg: 1600, max: 2800, min: 500, energy: 11.4 }, // House 3 - Townhouse
                4: { avg: 950,  max: 1800, min: 200, energy: 6.8 },  // House 4 - Small Apartment
                5: { avg: 1800, max: 3100, min: 600, energy: 12.9 }, // House 5 - Medium Villa
            };

            const defaults = houseDefaults[user?.ukdale_house_id] || houseDefaults[1];

            return {
                avgPower: defaults.avg,  // Return number, not string
                maxPower: defaults.max,  // Return number, not string
                minPower: defaults.min,  // Return number, not string
                energyToday: defaults.energy
            };
        }

        const readings = userEnergyData.readings;
        const avg = readings.reduce((sum, r) => sum + r.power_watts, 0) / readings.length;
        const max = Math.max(...readings.map(r => r.power_watts));
        const min = Math.min(...readings.map(r => r.power_watts));
        const energyToday = (avg * 24 / 1000);

        return {
            avgPower: avg,
            maxPower: max,
            minPower: min,
            energyToday: energyToday
        };
    };

    // Get current data - prioritize user-specific data over WebSocket
    const getCurrentPower = () => {
        let power = 0;
        if (userEnergyData?.readings?.length > 0) {
            power = userEnergyData.readings[0].power_watts;
        } else {
            const avgPower = calculateUserStats().avgPower;
            power = realtimeData[selectedHousehold]?.current_power || avgPower;
        }
        // Ensure we return a number, not a string
        return typeof power === 'number' ? power : parseFloat(power) || 0;
    };

    const getCurrentCO2 = () => {
        if (userEnergyData?.readings?.length > 0) {
            return userEnergyData.readings[0].co2_kg;
        }
        return (getCurrentPower() / 1000 * 0.35);
    };

    const userStats = calculateUserStats();
    const currentPower = getCurrentPower();
    const currentCO2 = getCurrentCO2();

    // Update appliance data when power changes
    useEffect(() => {
        if (currentPower > 0) {
            updateApplianceBreakdown(currentPower);
        }
    }, [currentPower]);

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color="#10B981" />
                <Text style={styles.loadingText}>Loading your personalized energy data...</Text>
                {user?.ukdale_house_id && (
                    <Text style={styles.loadingSubText}>
                        Using UK-DALE House {user.ukdale_house_id} for your profile
                    </Text>
                )}
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
            {/* Header with User Info */}
            <View style={styles.header}>
                <View style={styles.headerRow}>
                    <View>
                        <Text style={styles.title}>Energy Dashboard</Text>
                        {user?.full_name && (
                            <Text style={styles.userName}>Welcome, {user.full_name}</Text>
                        )}
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: getConnectionColor() + '20' }]}>
                        <Ionicons name={getConnectionIcon()} size={14} color={getConnectionColor()} />
                        <Text style={[styles.statusText, { color: getConnectionColor() }]}>
                            {connectionStatus === 'connected' ? 'Live' : 'Offline'}
                        </Text>
                    </View>
                </View>
                <Text style={styles.subtitle}>Personalized for your {user?.home_type}</Text>

                {/* UK-DALE House Badge */}
                {user?.ukdale_house_id && (
                    <View style={styles.houseBadge}>
                        <Ionicons name="home" size={16} color="#fff" />
                        <Text style={styles.houseBadgeText}>
                            UK-DALE House {user.ukdale_house_id} · {user.home_type} · {user.bedrooms} beds
                        </Text>
                    </View>
                )}

                {/* NILM Status Badge */}
                {nilmAvailable && (
                    <View style={styles.nilmBadge}>
                        <Ionicons name="analytics" size={14} color="#10B981" />
                        <Text style={styles.nilmBadgeText}>NILM Enabled</Text>
                    </View>
                )}
            </View>

            {/* Live Power Card */}
            <Card style={styles.liveCard}>
                <Card.Content>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>Current Usage</Text>
                        <View style={styles.liveIndicator}>
                            <View style={styles.liveDot} />
                            <Text style={styles.liveText}>LIVE</Text>
                        </View>
                    </View>

                    <Text style={styles.powerValue}>
                        {formatPower(currentPower)} <Text style={styles.powerUnit}>W</Text>
                    </Text>

                    <View style={styles.co2Container}>
                        <Ionicons name="leaf" size={20} color="#10B981" />
                        <Text style={styles.co2Text}>
                            {formatCO2(currentCO2)} kg CO₂/hour
                        </Text>
                    </View>

                    <View style={styles.metricsRow}>
                        <View style={styles.metric}>
                            <Ionicons name="thermometer" size={16} color="#F59E0B" />
                            <Text style={styles.metricText}>
                                {userEnergyData?.readings?.[0]?.outside_temperature || '35'}°C
                            </Text>
                        </View>
                        <View style={styles.metric}>
                            <Ionicons name="location" size={16} color="#3B82F6" />
                            <Text style={styles.metricText}>{user?.emirate || 'Dubai'}</Text>
                        </View>
                        <View style={styles.metric}>
                            <Ionicons name="time" size={16} color="#6B7280" />
                            <Text style={styles.metricText}>
                                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </Text>
                        </View>
                    </View>
                </Card.Content>
            </Card>

            {/* Stats Grid */}
            <View style={styles.statsGrid}>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="trending-up" size={20} color="#10B981" />
                        <Text style={styles.statValue}>{formatPower(userStats.avgPower)}</Text>
                        <Text style={styles.statLabel}>Average Power</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="flash" size={20} color="#F59E0B" />
                        <Text style={styles.statValue}>{formatPower(userStats.maxPower)}</Text>
                        <Text style={styles.statLabel}>Peak Power</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="battery-half" size={20} color="#3B82F6" />
                        <Text style={styles.statValue}>{formatPower(userStats.minPower)}</Text>
                        <Text style={styles.statLabel}>Min Power</Text>
                    </Card.Content>
                </Card>
            </View>

            {/* User's Energy Data Preview */}
            {userEnergyData?.readings?.length > 0 && (
                <Card style={styles.dataPreviewCard}>
                    <Card.Content>
                        <Text style={styles.previewTitle}>
                            Your Recent Readings (House {userEnergyData.house_id})
                        </Text>
                        {userEnergyData.readings.slice(0, 5).map((reading, index) => (
                            <View key={index} style={styles.readingRow}>
                                <Text style={styles.readingTime}>
                                    {new Date(reading.timestamp).toLocaleTimeString()}
                                </Text>
                                <Text style={styles.readingPower}>
                                    {formatPower(reading.power_watts)} W
                                </Text>
                                <Text style={styles.readingCO2}>
                                    {formatCO2(reading.co2_kg)} kg
                                </Text>
                            </View>
                        ))}
                    </Card.Content>
                </Card>
            )}

            {/* Appliance Breakdown */}
            <Card style={styles.sectionCard}>
                <Card.Content>
                    <View style={styles.sectionHeader}>
                        <Text style={styles.sectionCardTitle}>Active Appliances</Text>
                        {nilmAvailable && (
                            <View style={styles.nilmBadge}>
                                <Ionicons name="analytics" size={12} color="#10B981" />
                                <Text style={styles.nilmBadgeText}>NILM</Text>
                            </View>
                        )}
                    </View>

                    {applianceList.length > 0 ? (
                        applianceList.map((appliance, idx) => (
                            <View key={idx} style={styles.applianceRow}>
                                <View style={[styles.applianceIcon, { backgroundColor: appliance.color }]}>
                                    <Ionicons name={appliance.icon} size={20} color="#10B981" />
                                </View>
                                <View style={styles.applianceInfo}>
                                    <Text style={styles.applianceName}>{appliance.name}</Text>
                                    <Text style={styles.appliancePower}>{formatPower(appliance.power)} W</Text>
                                </View>
                            </View>
                        ))
                    ) : (
                        <Text style={styles.noDataText}>No appliances detected</Text>
                    )}
                </Card.Content>
            </Card>

            {/* Daily Summary */}
            <Card style={styles.sectionCard}>
                <Card.Content>
                    <Text style={styles.sectionCardTitle}>Today's Summary</Text>
                    <View style={styles.summaryRow}>
                        <View style={styles.summaryItem}>
                            <Text style={styles.summaryLabel}>Energy Used</Text>
                            <Text style={styles.summaryValue}>{userStats.energyToday.toFixed(1)} kWh</Text>
                        </View>
                        <View style={styles.summaryItem}>
                            <Text style={styles.summaryLabel}>CO₂ Emitted</Text>
                            <Text style={styles.summaryValue}>
                                {(currentCO2 * 24).toFixed(1)} kg
                            </Text>
                        </View>
                        <View style={styles.summaryItem}>
                            <Text style={styles.summaryLabel}>Est. Cost</Text>
                            <Text style={styles.summaryValue}>
                                AED {(currentCO2 * 24 * 0.45).toFixed(2)}
                            </Text>
                        </View>
                    </View>
                </Card.Content>
            </Card>

            {/* House Comparison */}
            {user?.ukdale_house_id && (
                <Card style={styles.comparisonCard}>
                    <Card.Content>
                        <View style={styles.comparisonHeader}>
                            <Ionicons name="bar-chart" size={20} color="#10B981" />
                            <Text style={styles.comparisonTitle}>Compared to similar homes</Text>
                        </View>
                        <Text style={styles.comparisonText}>
                            Your energy usage is {userStats.avgPower > 2000 ? 'higher' : 'lower'} than average for {user.home_type}s in {user.emirate}.
                        </Text>
                        {applianceList.length > 0 && (
                            <Text style={styles.comparisonSubtext}>
                                Your {applianceList[0].name} uses {formatPower(applianceList[0].power)}W, which is typical for a {user.home_type}.
                            </Text>
                        )}
                    </Card.Content>
                </Card>
            )}
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F9FAFB',
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#F9FAFB',
        padding: 20,
    },
    loadingText: {
        marginTop: 16,
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
    },
    loadingSubText: {
        marginTop: 8,
        fontSize: 14,
        color: '#6B7280',
    },
    header: {
        backgroundColor: '#10B981',
        padding: 20,
    },
    headerRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#fff',
    },
    userName: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
        marginTop: 2,
    },
    statusBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 20,
    },
    statusText: {
        fontSize: 12,
        fontWeight: '600',
        marginLeft: 4,
    },
    subtitle: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
        marginTop: 4,
    },
    houseBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        marginTop: 10,
        alignSelf: 'flex-start',
    },
    houseBadgeText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '500',
        marginLeft: 6,
    },
    nilmBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#D1FAE5',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 16,
        marginTop: 8,
        alignSelf: 'flex-start',
    },
    nilmBadgeText: {
        fontSize: 11,
        color: '#065F46',
        fontWeight: '600',
        marginLeft: 4,
    },
    liveCard: {
        margin: 16,
        borderRadius: 16,
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
    },
    liveIndicator: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#FEE2E2',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
    },
    liveDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#EF4444',
        marginRight: 4,
    },
    liveText: {
        fontSize: 10,
        fontWeight: '600',
        color: '#EF4444',
    },
    powerValue: {
        fontSize: 48,
        fontWeight: 'bold',
        color: '#10B981',
        textAlign: 'center',
    },
    powerUnit: {
        fontSize: 20,
        color: '#9CA3AF',
        fontWeight: 'normal',
    },
    co2Container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#D1FAE5',
        padding: 12,
        borderRadius: 8,
        marginTop: 8,
    },
    co2Text: {
        marginLeft: 8,
        fontSize: 16,
        fontWeight: '600',
        color: '#065F46',
    },
    metricsRow: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        marginTop: 16,
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: '#F3F4F6',
    },
    metric: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    metricText: {
        marginLeft: 4,
        fontSize: 12,
        color: '#6B7280',
    },
    statsGrid: {
        flexDirection: 'row',
        marginHorizontal: 16,
        marginBottom: 16,
        gap: 12,
    },
    statCard: {
        flex: 1,
        borderRadius: 12,
    },
    statValue: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#111827',
        marginTop: 8,
    },
    statLabel: {
        fontSize: 11,
        color: '#6B7280',
        marginTop: 2,
    },
    dataPreviewCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#F0F9FF',
        borderRadius: 12,
    },
    previewTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#0369A1',
        marginBottom: 12,
    },
    readingRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: 6,
        borderBottomWidth: 1,
        borderBottomColor: '#E0F2FE',
    },
    readingTime: {
        fontSize: 12,
        color: '#4B5563',
    },
    readingPower: {
        fontSize: 12,
        fontWeight: '600',
        color: '#0369A1',
    },
    readingCO2: {
        fontSize: 12,
        color: '#059669',
    },
    sectionCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        borderRadius: 12,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    sectionCardTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
    },
    applianceRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    applianceIcon: {
        width: 40,
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    applianceInfo: {
        flex: 1,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    applianceName: {
        fontSize: 14,
        color: '#111827',
    },
    appliancePower: {
        fontSize: 14,
        fontWeight: '600',
        color: '#10B981',
    },
    noDataText: {
        fontSize: 14,
        color: '#6B7280',
        textAlign: 'center',
        padding: 20,
    },
    summaryRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    summaryItem: {
        alignItems: 'center',
    },
    summaryLabel: {
        fontSize: 12,
        color: '#6B7280',
        marginBottom: 4,
    },
    summaryValue: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
    },
    comparisonCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#F3F4F6',
        borderRadius: 12,
    },
    comparisonHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    comparisonTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#374151',
        marginLeft: 8,
    },
    comparisonText: {
        fontSize: 13,
        color: '#4B5563',
        lineHeight: 18,
        marginBottom: 4,
    },
    comparisonSubtext: {
        fontSize: 12,
        color: '#6B7280',
        lineHeight: 16,
    },
});

export default DashboardScreen;
import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    TouchableOpacity,
    Alert
} from 'react-native';
import { Card } from 'react-native-paper';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config/env';

const ProfileScreen = ({ navigation }) => {
    const { user, logout, isAuthenticated } = useAuth();
    const [userStats, setUserStats] = useState({
        missions: 0,
        tokens: 0,
        co2Saved: 0,
        energySaved: 0,
        houseId: null,
        totalMissions: 0
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user?.id) {
            loadUserStats(user.id);
        } else {
            setLoading(false);
        }
    }, [user]);

    const loadUserStats = async (userId) => {
        try {
            console.log(`📊 Loading profile stats for user ${userId}`);
            const response = await fetch(`${API_BASE_URL}/api/user/stats/${userId}`);
            const data = await response.json();
            
            setUserStats({
                missions: data.missions_completed || 0,
                tokens: data.current_balance || 0,
                co2Saved: data.total_co2_saved || 0,
                energySaved: data.energy_saved || 0,
                houseId: data.ukdale_house_id,
                totalMissions: data.total_missions || 0
            });
        } catch (error) {
            console.error('Error loading user stats:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        Alert.alert(
            'Logout',
            'Are you sure you want to logout?',
            [
                { text: 'Cancel', style: 'cancel' },
                { 
                    text: 'Logout', 
                    onPress: async () => {
                        await logout();
                        navigation.replace('Login');
                    },
                    style: 'destructive'
                }
            ]
        );
    };

    if (!isAuthenticated || !user) {
        return (
            <View style={styles.centerContainer}>
                <Ionicons name="person-circle-outline" size={80} color="#D1D5DB" />
                <Text style={styles.notLoggedInText}>Not logged in</Text>
                <TouchableOpacity 
                    style={styles.loginButton}
                    onPress={() => navigation.navigate('Login')}
                >
                    <Text style={styles.loginButtonText}>Go to Login</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // Calculate completion rate
    const completionRate = userStats.totalMissions > 0 
        ? Math.round((userStats.missions / userStats.totalMissions) * 100) 
        : 0;

    return (
        <ScrollView style={styles.container}>
            {/* Profile Header */}
            <View style={styles.header}>
                <View style={styles.avatarContainer}>
                    <Text style={styles.avatarText}>
                        {user.full_name?.charAt(0) || user.username?.charAt(0) || 'U'}
                    </Text>
                </View>
                <Text style={styles.userName}>{user.full_name || user.username}</Text>
                <Text style={styles.userEmail}>{user.email}</Text>
                
                {/* UK-DALE House Badge */}
                {userStats.houseId && (
                    <View style={styles.houseBadge}>
                        <Ionicons name="home" size={14} color="#10B981" />
                        <Text style={styles.houseBadgeText}>
                            UK-DALE House {userStats.houseId}
                        </Text>
                    </View>
                )}
            </View>

            {/* Stats Cards - Now with real data */}
            <View style={styles.statsRow}>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="flash" size={24} color="#10B981" />
                        <Text style={styles.statNumber}>{userStats.energySaved}</Text>
                        <Text style={styles.statLabel}>kWh saved</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="leaf" size={24} color="#10B981" />
                        <Text style={styles.statNumber}>{userStats.co2Saved}</Text>
                        <Text style={styles.statLabel}>kg CO₂</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="trophy" size={24} color="#10B981" />
                        <Text style={styles.statNumber}>{userStats.missions}</Text>
                        <Text style={styles.statLabel}>Missions</Text>
                    </Card.Content>
                </Card>
            </View>

            {/* Mission Completion Rate */}
            {userStats.totalMissions > 0 && (
                <Card style={styles.completionCard}>
                    <Card.Content>
                        <View style={styles.completionHeader}>
                            <Ionicons name="trending-up" size={20} color="#10B981" />
                            <Text style={styles.completionTitle}>Mission Completion Rate</Text>
                        </View>
                        <View style={styles.progressContainer}>
                            <View style={[styles.progressBar, { width: `${completionRate}%` }]} />
                        </View>
                        <Text style={styles.completionText}>
                            {completionRate}% · {userStats.missions}/{userStats.totalMissions} missions completed
                        </Text>
                    </Card.Content>
                </Card>
            )}

            {/* Personal Information */}
            <Card style={styles.sectionCard}>
                <Card.Content>
                    <Text style={styles.sectionTitle}>Personal Information</Text>
                    
                    <View style={styles.infoRow}>
                        <Ionicons name="location-outline" size={20} color="#6B7280" />
                        <View style={styles.infoContent}>
                            <Text style={styles.infoLabel}>Emirate</Text>
                            <Text style={styles.infoValue}>{user.emirate || 'Dubai'}</Text>
                        </View>
                    </View>

                    <View style={styles.infoRow}>
                        <Ionicons name="home-outline" size={20} color="#6B7280" />
                        <View style={styles.infoContent}>
                            <Text style={styles.infoLabel}>Home Type</Text>
                            <Text style={styles.infoValue}>
                                {user.home_type || 'Villa'} · {user.bedrooms || '3'} bedrooms
                            </Text>
                        </View>
                    </View>

                    <View style={styles.infoRow}>
                        <Ionicons name="car-outline" size={20} color="#6B7280" />
                        <View style={styles.infoContent}>
                            <Text style={styles.infoLabel}>Vehicle</Text>
                            <Text style={styles.infoValue}>
                                {user.vehicle_type || 'SUV'} · {user.vehicle_fuel || 'Petrol'}
                            </Text>
                        </View>
                    </View>

                    <View style={styles.infoRow}>
                        <Ionicons name="calendar-outline" size={20} color="#6B7280" />
                        <View style={styles.infoContent}>
                            <Text style={styles.infoLabel}>Member since</Text>
                            <Text style={styles.infoValue}>
                                {new Date(user.created_at || Date.now()).toLocaleDateString('en-GB', {
                                    day: 'numeric',
                                    month: 'short',
                                    year: 'numeric'
                                })}
                            </Text>
                        </View>
                    </View>

                    {/* Impact Summary */}
                    {userStats.co2Saved > 0 && (
                        <View style={styles.impactContainer}>
                            <Text style={styles.impactText}>
                                🌳 Your CO₂ savings = {Math.round(userStats.co2Saved / 21.77)} trees planted
                            </Text>
                        </View>
                    )}
                </Card.Content>
            </Card>

            {/* Preferences */}
            <Card style={styles.sectionCard}>
                <Card.Content>
                    <Text style={styles.sectionTitle}>Preferences</Text>

                    <View style={styles.preferenceRow}>
                        <View style={styles.preferenceLeft}>
                            <Ionicons name="notifications-outline" size={20} color="#6B7280" />
                            <Text style={styles.preferenceLabel}>Push Notifications</Text>
                        </View>
                        <View style={styles.preferenceRight}>
                            <Text style={styles.preferenceValue}>On</Text>
                            <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
                        </View>
                    </View>

                    <View style={styles.preferenceRow}>
                        <View style={styles.preferenceLeft}>
                            <Ionicons name="moon-outline" size={20} color="#6B7280" />
                            <Text style={styles.preferenceLabel}>Dark Mode</Text>
                        </View>
                        <View style={styles.preferenceRight}>
                            <Text style={styles.preferenceValue}>Off</Text>
                            <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
                        </View>
                    </View>

                    <View style={styles.preferenceRow}>
                        <View style={styles.preferenceLeft}>
                            <Ionicons name="language-outline" size={20} color="#6B7280" />
                            <Text style={styles.preferenceLabel}>Language</Text>
                        </View>
                        <View style={styles.preferenceRight}>
                            <Text style={styles.preferenceValue}>English</Text>
                            <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
                        </View>
                    </View>
                </Card.Content>
            </Card>

            {/* Token Balance - Now with real data */}
            <Card style={styles.tokenCard}>
                <Card.Content>
                    <View style={styles.tokenHeader}>
                        <Ionicons name="trophy" size={24} color="#F59E0B" />
                        <Text style={styles.tokenTitle}>Green Tokens</Text>
                    </View>
                    <Text style={styles.tokenBalance}>{userStats.tokens}</Text>
                    <Text style={styles.tokenSubtext}>Available to redeem</Text>
                    
                    <TouchableOpacity 
                        style={styles.redeemButton}
                        onPress={() => Alert.alert('Coming Soon', 'Rewards store coming soon!')}
                    >
                        <Text style={styles.redeemButtonText}>Redeem Rewards</Text>
                    </TouchableOpacity>
                </Card.Content>
            </Card>

            {/* Achievements Preview */}
            {userStats.missions >= 5 && (
                <Card style={styles.achievementCard}>
                    <Card.Content>
                        <View style={styles.achievementHeader}>
                            <Ionicons name="ribbon" size={20} color="#F59E0B" />
                            <Text style={styles.achievementTitle}>Achievements</Text>
                        </View>
                        <View style={styles.achievementGrid}>
                            {userStats.missions >= 5 && (
                                <View style={styles.achievementItem}>
                                    <Ionicons name="star" size={24} color="#F59E0B" />
                                    <Text style={styles.achievementText}>5 Missions</Text>
                                </View>
                            )}
                            {userStats.missions >= 10 && (
                                <View style={styles.achievementItem}>
                                    <Ionicons name="star" size={24} color="#F59E0B" />
                                    <Text style={styles.achievementText}>10 Missions</Text>
                                </View>
                            )}
                            {userStats.co2Saved >= 50 && (
                                <View style={styles.achievementItem}>
                                    <Ionicons name="leaf" size={24} color="#10B981" />
                                    <Text style={styles.achievementText}>50kg CO₂</Text>
                                </View>
                            )}
                        </View>
                    </Card.Content>
                </Card>
            )}

            {/* Logout Button */}
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
                <Ionicons name="log-out-outline" size={20} color="#EF4444" />
                <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>

            <View style={styles.footer}>
                <Text style={styles.footerText}>CarbonLife</Text>
                <Text style={styles.footerSubtext}>Version 1.0.0</Text>
            </View>
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
    notLoggedInText: {
        fontSize: 18,
        color: '#6B7280',
        marginTop: 12,
        marginBottom: 20,
    },
    loginButton: {
        backgroundColor: '#10B981',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 8,
    },
    loginButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    header: {
        backgroundColor: '#10B981',
        padding: 30,
        alignItems: 'center',
    },
    avatarContainer: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: '#fff',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    avatarText: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#10B981',
    },
    userName: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 4,
    },
    userEmail: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
    },
    houseBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 16,
        marginTop: 8,
    },
    houseBadgeText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: '500',
        marginLeft: 6,
    },
    statsRow: {
        flexDirection: 'row',
        marginHorizontal: 16,
        marginTop: -20,
        marginBottom: 16,
        gap: 12,
    },
    statCard: {
        flex: 1,
        borderRadius: 12,
        elevation: 4,
    },
    statNumber: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#111827',
        marginTop: 8,
    },
    statLabel: {
        fontSize: 11,
        color: '#6B7280',
    },
    completionCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#F0F9FF',
        borderRadius: 12,
    },
    completionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    completionTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#0369A1',
        marginLeft: 8,
    },
    progressContainer: {
        height: 8,
        backgroundColor: '#E0F2FE',
        borderRadius: 4,
        marginBottom: 8,
        overflow: 'hidden',
    },
    progressBar: {
        height: '100%',
        backgroundColor: '#10B981',
    },
    completionText: {
        fontSize: 12,
        color: '#4B5563',
    },
    sectionCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        borderRadius: 12,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
        marginBottom: 16,
    },
    infoRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    infoContent: {
        marginLeft: 12,
        flex: 1,
    },
    infoLabel: {
        fontSize: 12,
        color: '#6B7280',
        marginBottom: 2,
    },
    infoValue: {
        fontSize: 16,
        color: '#111827',
        fontWeight: '500',
    },
    impactContainer: {
        marginTop: 8,
        padding: 12,
        backgroundColor: '#F0FDF4',
        borderRadius: 8,
    },
    impactText: {
        fontSize: 13,
        color: '#065F46',
        fontWeight: '500',
    },
    preferenceRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#F3F4F6',
    },
    preferenceLeft: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    preferenceLabel: {
        fontSize: 14,
        color: '#111827',
        marginLeft: 12,
    },
    preferenceRight: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    preferenceValue: {
        fontSize: 14,
        color: '#6B7280',
        marginRight: 8,
    },
    tokenCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#FEF3C7',
        borderRadius: 12,
    },
    tokenHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    tokenTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#92400E',
        marginLeft: 8,
    },
    tokenBalance: {
        fontSize: 36,
        fontWeight: 'bold',
        color: '#92400E',
    },
    tokenSubtext: {
        fontSize: 12,
        color: '#B45309',
        marginBottom: 16,
    },
    redeemButton: {
        backgroundColor: '#F59E0B',
        padding: 12,
        borderRadius: 8,
        alignItems: 'center',
    },
    redeemButtonText: {
        color: '#fff',
        fontWeight: '600',
        fontSize: 14,
    },
    achievementCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#FFFBEB',
        borderWidth: 1,
        borderColor: '#FDE68A',
        borderRadius: 12,
    },
    achievementHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    achievementTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#92400E',
        marginLeft: 8,
    },
    achievementGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
    },
    achievementItem: {
        alignItems: 'center',
        minWidth: 70,
    },
    achievementText: {
        fontSize: 11,
        color: '#92400E',
        marginTop: 4,
        textAlign: 'center',
    },
    logoutButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        marginHorizontal: 16,
        marginBottom: 16,
        padding: 16,
        backgroundColor: '#FEE2E2',
        borderRadius: 12,
    },
    logoutText: {
        color: '#EF4444',
        fontSize: 16,
        fontWeight: '600',
        marginLeft: 8,
    },
    footer: {
        alignItems: 'center',
        marginBottom: 20,
    },
    footerText: {
        fontSize: 14,
        color: '#10B981',
        fontWeight: '600',
    },
    footerSubtext: {
        fontSize: 12,
        color: '#9CA3AF',
        marginTop: 4,
    },
});

export default ProfileScreen;
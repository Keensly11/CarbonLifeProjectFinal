import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    TouchableOpacity
} from 'react-native';
import { Card } from 'react-native-paper';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config/env';

const HomeScreen = ({ navigation }) => {
    const { user } = useAuth();
    const [userStats, setUserStats] = useState({
        missions: 0,
        co2Saved: 0,
        tokens: 0,
        energyToday: 0,
        houseId: null
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
            console.log(`📊 Loading stats for user ${userId}`);
            const response = await fetch(`${API_BASE_URL}/api/user/stats/${userId}`);
            const data = await response.json();
            
            setUserStats({
                missions: data.missions_completed || 0,
                co2Saved: data.total_co2_saved || 0,
                tokens: data.current_balance || 0,
                energyToday: data.energy_today || 0,
                houseId: data.ukdale_house_id
            });
        } catch (error) {
            console.error('Error loading user stats:', error);
        } finally {
            setLoading(false);
        }
    };

    // Get personalized greeting based on time of day
    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 18) return 'Good afternoon';
        return 'Good evening';
    };

    return (
        <ScrollView style={styles.container}>
            {/* Header with personalized greeting */}
            <View style={styles.header}>
                <Text style={styles.greeting}>
                    {getGreeting()}
                    {user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
                </Text>
                <Text style={styles.appName}>CarbonLife</Text>
                <View style={styles.uaeBadge}>
                    <Ionicons name="location" size={16} color="#fff" />
                    <Text style={styles.uaeText}>United Arab Emirates</Text>
                </View>
                
                {/* UK-DALE House Badge - shows which house their data comes from */}
                {userStats.houseId && (
                    <View style={styles.houseBadge}>
                        <Ionicons name="home" size={14} color="#10B981" />
                        <Text style={styles.houseBadgeText}>
                            Your energy profile: UK-DALE House {userStats.houseId}
                        </Text>
                    </View>
                )}
            </View>

            {/* Hero Card with personalized message */}
            <Card style={styles.heroCard}>
                <Card.Content>
                    <Text style={styles.heroTitle}>
                        {user?.full_name ? `Welcome back, ${user.full_name.split(' ')[0]}!` : 'Welcome to CarbonLife!'}
                    </Text>
                    <Text style={styles.heroText}>
                        {userStats.missions > 0 
                            ? `You've completed ${userStats.missions} missions and saved ${userStats.co2Saved}kg of CO₂. Keep up the great work!`
                            : 'Track your energy usage, complete eco-friendly missions, and earn rewards while helping the UAE reach Net Zero 2050.'}
                    </Text>
                    <TouchableOpacity 
                        style={styles.heroButton}
                        onPress={() => navigation.navigate('Dashboard')}
                    >
                        <Text style={styles.heroButtonText}>View Your Impact</Text>
                        <Ionicons name="arrow-forward" size={18} color="#fff" />
                    </TouchableOpacity>
                </Card.Content>
            </Card>

            {/* Quick Stats Row - Now with real data */}
            <View style={styles.statsRow}>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="leaf" size={24} color="#10B981" />
                        <Text style={styles.statNumber}>{userStats.co2Saved}</Text>
                        <Text style={styles.statLabel}>kg CO₂ Saved</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="flash" size={24} color="#F59E0B" />
                        <Text style={styles.statNumber}>{userStats.energyToday}</Text>
                        <Text style={styles.statLabel}>kWh Today</Text>
                    </Card.Content>
                </Card>
                <Card style={styles.statCard}>
                    <Card.Content>
                        <Ionicons name="trophy" size={24} color="#3B82F6" />
                        <Text style={styles.statNumber}>{userStats.missions}</Text>
                        <Text style={styles.statLabel}>Missions</Text>
                    </Card.Content>
                </Card>
            </View>

            {/* Token Balance Card */}
            {userStats.tokens > 0 && (
                <Card style={styles.tokenCard}>
                    <Card.Content>
                        <View style={styles.tokenHeader}>
                            <Ionicons name="trophy" size={24} color="#F59E0B" />
                            <Text style={styles.tokenTitle}>Green Tokens Balance</Text>
                        </View>
                        <Text style={styles.tokenBalance}>{userStats.tokens} tokens</Text>
                        <TouchableOpacity 
                            style={styles.redeemButton}
                            onPress={() => navigation.navigate('Profile')}
                        >
                            <Text style={styles.redeemButtonText}>Redeem Rewards</Text>
                        </TouchableOpacity>
                    </Card.Content>
                </Card>
            )}

            {/* Features Grid */}
            <Text style={styles.sectionTitle}>What you can do</Text>
            
            <View style={styles.featuresGrid}>
                <TouchableOpacity 
                    style={styles.featureItem}
                    onPress={() => navigation.navigate('Dashboard')}
                >
                    <View style={[styles.featureIcon, { backgroundColor: '#D1FAE5' }]}>
                        <Ionicons name="speedometer" size={28} color="#10B981" />
                    </View>
                    <Text style={styles.featureTitle}>Live Dashboard</Text>
                    <Text style={styles.featureDesc}>See your energy in real-time</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                    style={styles.featureItem}
                    onPress={() => navigation.navigate('Recommendations')}
                >
                    <View style={[styles.featureIcon, { backgroundColor: '#FEF3C7' }]}>
                        <Ionicons name="bulb" size={28} color="#F59E0B" />
                    </View>
                    <Text style={styles.featureTitle}>Smart Tips</Text>
                    <Text style={styles.featureDesc}>Personalized recommendations</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                    style={styles.featureItem}
                    onPress={() => navigation.navigate('Profile')}
                >
                    <View style={[styles.featureIcon, { backgroundColor: '#DBEAFE' }]}>
                        <Ionicons name="person" size={28} color="#3B82F6" />
                    </View>
                    <Text style={styles.featureTitle}>Your Profile</Text>
                    <Text style={styles.featureDesc}>Track your progress</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                    style={styles.featureItem}
                    onPress={() => navigation.navigate('Profile')}
                >
                    <View style={[styles.featureIcon, { backgroundColor: '#FCE7F3' }]}>
                        <Ionicons name="gift" size={28} color="#EC4899" />
                    </View>
                    <Text style={styles.featureTitle}>Rewards</Text>
                    <Text style={styles.featureDesc}>Earn and redeem tokens</Text>
                </TouchableOpacity>
            </View>

            {/* Daily Tip - Could also be personalized based on user's house */}
            <Card style={styles.tipCard}>
                <Card.Content>
                    <View style={styles.tipHeader}>
                        <Ionicons name="leaf" size={20} color="#10B981" />
                        <Text style={styles.tipTitle}>Today's Tip</Text>
                    </View>
                    <Text style={styles.tipText}>
                        {user?.home_type === 'Villa'
                            ? 'For villas: Setting your AC to 24°C instead of 22°C can save up to 15% on your energy bill.'
                            : user?.home_type === 'Apartment'
                            ? 'For apartments: Using ceiling fans allows you to raise the AC temperature by 2°C without reducing comfort.'
                            : 'Setting your AC to 24°C instead of 22°C can save up to 10% on your energy bill.'}
                    </Text>
                </Card.Content>
            </Card>

            {/* Progress Message if they have missions */}
            {userStats.missions > 0 && (
                <Card style={styles.progressCard}>
                    <Card.Content>
                        <View style={styles.progressHeader}>
                            <Ionicons name="trending-up" size={20} color="#10B981" />
                            <Text style={styles.progressTitle}>Your Impact</Text>
                        </View>
                        <Text style={styles.progressText}>
                            You've saved {userStats.co2Saved}kg of CO₂ - that's like planting {Math.round(userStats.co2Saved / 21.77)} trees! 🌳
                        </Text>
                    </Card.Content>
                </Card>
            )}

            {/* UAE Vision */}
            <View style={styles.visionContainer}>
                <Text style={styles.visionText}>
                    Supporting the UAE's Net Zero 2050 initiative
                </Text>
            </View>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F9FAFB',
    },
    header: {
        padding: 20,
        paddingBottom: 10,
    },
    greeting: {
        fontSize: 16,
        color: '#6B7280',
    },
    appName: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#10B981',
        marginBottom: 8,
    },
    uaeBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#10B981',
        alignSelf: 'flex-start',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        marginBottom: 8,
    },
    uaeText: {
        color: '#fff',
        fontSize: 14,
        fontWeight: '500',
        marginLeft: 4,
    },
    houseBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#F3F4F6',
        alignSelf: 'flex-start',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 16,
        marginTop: 4,
    },
    houseBadgeText: {
        fontSize: 12,
        color: '#10B981',
        fontWeight: '500',
        marginLeft: 4,
    },
    heroCard: {
        margin: 16,
        backgroundColor: '#10B981',
        borderRadius: 16,
    },
    heroTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 8,
    },
    heroText: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
        lineHeight: 20,
        marginBottom: 16,
    },
    heroButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 8,
        alignSelf: 'flex-start',
    },
    heroButtonText: {
        color: '#fff',
        fontWeight: '600',
        marginRight: 8,
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        marginBottom: 16,
    },
    statCard: {
        flex: 1,
        marginHorizontal: 4,
        borderRadius: 12,
        elevation: 2,
    },
    statNumber: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#111827',
        marginTop: 8,
    },
    statLabel: {
        fontSize: 12,
        color: '#6B7280',
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
        fontSize: 32,
        fontWeight: 'bold',
        color: '#92400E',
        marginBottom: 12,
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
    sectionTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
        marginHorizontal: 16,
        marginBottom: 12,
    },
    featuresGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        paddingHorizontal: 12,
        marginBottom: 24,
    },
    featureItem: {
        width: '50%',
        paddingHorizontal: 4,
        marginBottom: 12,
    },
    featureIcon: {
        width: 56,
        height: 56,
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 8,
    },
    featureTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
        marginBottom: 2,
    },
    featureDesc: {
        fontSize: 12,
        color: '#6B7280',
    },
    tipCard: {
        margin: 16,
        backgroundColor: '#F0FDF4',
        borderWidth: 1,
        borderColor: '#D1FAE5',
        borderRadius: 12,
    },
    tipHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    tipTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#10B981',
        marginLeft: 8,
    },
    tipText: {
        fontSize: 14,
        color: '#374151',
        lineHeight: 20,
    },
    progressCard: {
        marginHorizontal: 16,
        marginBottom: 16,
        backgroundColor: '#EFF6FF',
        borderWidth: 1,
        borderColor: '#BFDBFE',
        borderRadius: 12,
    },
    progressHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    progressTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#1E40AF',
        marginLeft: 8,
    },
    progressText: {
        fontSize: 14,
        color: '#1E3A8A',
        lineHeight: 20,
    },
    visionContainer: {
        padding: 20,
        alignItems: 'center',
    },
    visionText: {
        fontSize: 12,
        color: '#9CA3AF',
        textAlign: 'center',
    },
});

export default HomeScreen;
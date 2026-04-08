import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    ActivityIndicator,
    RefreshControl,
    TouchableOpacity,
    Alert,
    Modal
} from 'react-native';
import { Card } from 'react-native-paper';
import Ionicons from 'react-native-vector-icons/Ionicons';
import mlRecommendationsService from '../services/mlRecommendationsService';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config/env';

const RecommendationsScreen = () => {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [recommendations, setRecommendations] = useState([]);
    const [activeMissions, setActiveMissions] = useState([]);
    const [completedMissions, setCompletedMissions] = useState([]);
    const [selectedMission, setSelectedMission] = useState(null);
    const [modalVisible, setModalVisible] = useState(false);
    const [activeTab, setActiveTab] = useState('recommended');
    const [mlError, setMlError] = useState(null);
    const { user } = useAuth();

    useEffect(() => {
        loadRecommendations();
        loadActiveMissions();
        loadCompletedMissions();
    }, []);

    const loadRecommendations = async () => {
        setLoading(true);
        setMlError(null);
        try {
            const userId = user?.id || 1;
            console.log('🎯 Fetching ML recommendations for user:', userId);
            
            const data = await mlRecommendationsService.getPersonalizedRecommendations(userId, 5);
            
            setRecommendations(data);
            console.log(`✅ Loaded ${data.length} ML-powered recommendations`);
        } catch (error) {
            console.error('❌ ML recommendation service failed:', error);
            setMlError(error.message);
            setRecommendations([]);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const loadActiveMissions = () => {
        // Load from AsyncStorage or backend
        const mockActive = [
            {
                id: 'active_1',
                title: 'Reduce AC during peak hours',
                description: 'Set thermostat 2°C higher from 2-5 PM',
                category: 'energy',
                difficulty: 'easy',
                tokens_reward: 75,
                savings_kg_co2: 3.5,
                accepted_at: new Date().toISOString(),
                time_remaining: '2h 15m',
                progress: 65
            }
        ];
        setActiveMissions(mockActive);
    };

    const loadCompletedMissions = () => {
        // Load from AsyncStorage or backend
        const mockCompleted = [
            {
                id: 'completed_1',
                title: 'Take Dubai Metro',
                description: 'Used public transport instead of car',
                category: 'transport',
                tokens_earned: 100,
                co2_saved: 8.5,
                completed_at: new Date().toISOString()
            }
        ];
        setCompletedMissions(mockCompleted);
    };

    const onRefresh = () => {
        setRefreshing(true);
        loadRecommendations();
    };

    const handleAcceptMission = (mission) => {
        Alert.alert(
            'Accept Mission',
            mission.personalized_message || mission.description,
            [
                { text: 'Cancel', style: 'cancel' },
                { 
                    text: 'Accept & Start', 
                    onPress: () => startMission(mission)
                }
            ]
        );
    };

    const startMission = (mission) => {
        setRecommendations(recommendations.filter(r => r.id !== mission.id));
        
        const activeMission = {
            ...mission,
            accepted_at: new Date().toISOString(),
            time_remaining: mission.estimated_time || '30 min',
            progress: 0,
            status: 'active'
        };
        setActiveMissions([...activeMissions, activeMission]);
        
        Alert.alert(
            '✅ Mission Started!',
            `You've accepted: ${mission.title}\n\nComplete it to earn ${mission.tokens_reward} tokens!`,
            [{ text: 'Let\'s do this!' }]
        );
        
        setActiveTab('active');
    };

    const handleCompleteMission = (mission) => {
        setSelectedMission(mission);
        setModalVisible(true);
    };

    const confirmCompletion = () => {
        if (!selectedMission) return;
        
        setActiveMissions(activeMissions.filter(m => m.id !== selectedMission.id));
        
        const completedMission = {
            ...selectedMission,
            completed_at: new Date().toISOString(),
            tokens_earned: selectedMission.tokens_reward,
            co2_saved: selectedMission.savings_kg_co2
        };
        setCompletedMissions([...completedMissions, completedMission]);
        
        Alert.alert(
            '🎉 Mission Complete!',
            `You earned ${selectedMission.tokens_reward} green tokens!\n\nCO₂ Saved: ${selectedMission.savings_kg_co2}kg`,
            [
                { 
                    text: 'Awesome!', 
                    onPress: () => {
                        setModalVisible(false);
                        setSelectedMission(null);
                    }
                }
            ]
        );
    };

    const cancelMission = (mission) => {
        Alert.alert(
            'Cancel Mission',
            'Are you sure you want to cancel this mission?',
            [
                { text: 'No, keep it', style: 'cancel' },
                { 
                    text: 'Yes, cancel', 
                    style: 'destructive',
                    onPress: () => {
                        setActiveMissions(activeMissions.filter(m => m.id !== mission.id));
                    }
                }
            ]
        );
    };

    const getCategoryIcon = (category) => {
        switch (category?.toLowerCase()) {
            case 'energy': return 'flash';
            case 'transport': return 'car';
            default: return 'leaf';
        }
    };

    const getCategoryColor = (category) => {
        switch (category?.toLowerCase()) {
            case 'energy': return '#10B981';
            case 'transport': return '#3B82F6';
            default: return '#8B5CF6';
        }
    };

    const getDifficultyColor = (difficulty) => {
        switch (difficulty?.toLowerCase()) {
            case 'easy': return '#10B981';
            case 'medium': return '#F59E0B';
            case 'hard': return '#EF4444';
            default: return '#6B7280';
        }
    };

    const formatTime = (isoString) => {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    if (loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color="#10B981" />
                <Text style={styles.loadingText}>ML Model analyzing your profile...</Text>
                <Text style={styles.loadingSubText}>Personalizing recommendations just for you</Text>
            </View>
        );
    }

    return (
        <>
            <ScrollView
                style={styles.container}
                refreshControl={
                    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                }
            >
                <View style={styles.header}>
                    <View style={styles.headerRow}>
                        <Text style={styles.title}>Missions</Text>
                        <View style={styles.mlBadge}>
                            <Ionicons name="brain" size={16} color="#8B5CF6" />
                            <Text style={styles.mlBadgeText}>ML v1.0</Text>
                        </View>
                    </View>
                    <Text style={styles.subtitle}>AI-powered recommendations</Text>
                </View>

                {/* ML Error State - No Fallback! */}
                {mlError && (
                    <Card style={styles.errorCard}>
                        <Card.Content>
                            <Ionicons name="alert-circle" size={48} color="#EF4444" />
                            <Text style={styles.errorTitle}>ML Service Unavailable</Text>
                            <Text style={styles.errorText}>{mlError}</Text>
                            <Text style={styles.errorSubtext}>
                                The ML model is currently unavailable. Please try again later.
                            </Text>
                            <TouchableOpacity style={styles.retryButton} onPress={loadRecommendations}>
                                <Text style={styles.retryButtonText}>Retry</Text>
                            </TouchableOpacity>
                        </Card.Content>
                    </Card>
                )}

                {/* Only show content if ML is working */}
                {!mlError && (
                    <>
                        {/* Tab Navigation */}
                        <View style={styles.tabContainer}>
                            <TouchableOpacity
                                style={[styles.tab, activeTab === 'recommended' && styles.activeTab]}
                                onPress={() => setActiveTab('recommended')}
                            >
                                <Text style={[styles.tabText, activeTab === 'recommended' && styles.activeTabText]}>
                                    Recommended ({recommendations.length})
                                </Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.tab, activeTab === 'active' && styles.activeTab]}
                                onPress={() => setActiveTab('active')}
                            >
                                <Text style={[styles.tabText, activeTab === 'active' && styles.activeTabText]}>
                                    Active ({activeMissions.length})
                                </Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.tab, activeTab === 'completed' && styles.activeTab]}
                                onPress={() => setActiveTab('completed')}
                            >
                                <Text style={[styles.tabText, activeTab === 'completed' && styles.activeTabText]}>
                                    Completed ({completedMissions.length})
                                </Text>
                            </TouchableOpacity>
                        </View>

                        {/* RECOMMENDED TAB - ML Generated Only */}
                        {activeTab === 'recommended' && (
                            <>
                                {recommendations.map((mission, index) => (
                                    <Card key={mission.id || index} style={styles.missionCard}>
                                        <Card.Content>
                                            <View style={styles.missionHeader}>
                                                <View style={[styles.categoryBadge, { backgroundColor: getCategoryColor(mission.category) + '20' }]}>
                                                    <Ionicons 
                                                        name={getCategoryIcon(mission.category)} 
                                                        size={14} 
                                                        color={getCategoryColor(mission.category)} 
                                                    />
                                                    <Text style={[styles.categoryText, { color: getCategoryColor(mission.category) }]}>
                                                        {mission.category?.toUpperCase() || 'ENERGY'}
                                                    </Text>
                                                </View>
                                                {mission.relevance_score && (
                                                    <View style={styles.scoreBadge}>
                                                        <Ionicons name="trending-up" size={12} color="#10B981" />
                                                        <Text style={styles.scoreText}>{mission.relevance_score}% ML match</Text>
                                                    </View>
                                                )}
                                            </View>

                                            <Text style={styles.missionTitle}>{mission.title}</Text>
                                            <Text style={styles.missionDescription}>
                                                {mission.personalized_message || mission.description}
                                            </Text>

                                            <View style={styles.detailsRow}>
                                                <View style={styles.detailItem}>
                                                    <Ionicons name="time" size={14} color="#6B7280" />
                                                    <Text style={styles.detailText}>{mission.estimated_time || '5 min'}</Text>
                                                </View>
                                                <View style={[styles.detailItem, { backgroundColor: getDifficultyColor(mission.difficulty) + '20' }]}>
                                                    <Ionicons name="speedometer" size={14} color={getDifficultyColor(mission.difficulty)} />
                                                    <Text style={[styles.detailText, { color: getDifficultyColor(mission.difficulty) }]}>
                                                        {mission.difficulty?.toUpperCase() || 'EASY'}
                                                    </Text>
                                                </View>
                                            </View>

                                            <View style={styles.rewardsRow}>
                                                <View style={styles.rewardItem}>
                                                    <Ionicons name="trophy" size={16} color="#F59E0B" />
                                                    <Text style={styles.rewardText}>{mission.tokens_reward || 50} tokens</Text>
                                                </View>
                                                <View style={styles.rewardItem}>
                                                    <Ionicons name="leaf" size={16} color="#10B981" />
                                                    <Text style={styles.rewardText}>Save {mission.savings_kg_co2 || '2.5'}kg CO₂</Text>
                                                </View>
                                            </View>

                                            <TouchableOpacity
                                                style={styles.acceptButton}
                                                onPress={() => handleAcceptMission(mission)}
                                            >
                                                <Text style={styles.acceptButtonText}>Accept Mission</Text>
                                                <Ionicons name="arrow-forward" size={16} color="#fff" />
                                            </TouchableOpacity>

                                            {/* ML Confidence Indicator */}
                                            {mission.ml_confidence && (
                                                <View style={styles.confidenceContainer}>
                                                    <View style={styles.confidenceLabel}>
                                                        <Text style={styles.confidenceText}>ML Confidence</Text>
                                                        <Text style={styles.confidenceValue}>{Math.round(mission.ml_confidence * 100)}%</Text>
                                                    </View>
                                                    <View style={styles.confidenceBar}>
                                                        <View style={[styles.confidenceFill, { width: `${mission.ml_confidence * 100}%` }]} />
                                                    </View>
                                                </View>
                                            )}
                                        </Card.Content>
                                    </Card>
                                ))}

                                {recommendations.length === 0 && !mlError && (
                                    <Card style={styles.emptyCard}>
                                        <Card.Content>
                                            <Ionicons name="checkmark-done-circle" size={48} color="#D1D5DB" />
                                            <Text style={styles.emptyTitle}>All Caught Up!</Text>
                                            <Text style={styles.emptyText}>
                                                No new ML recommendations right now. Check back later!
                                            </Text>
                                        </Card.Content>
                                    </Card>
                                )}
                            </>
                        )}

                        {/* ACTIVE TAB */}
                        {activeTab === 'active' && (
                            <>
                                {activeMissions.map((mission, index) => (
                                    <Card key={mission.id || index} style={styles.missionCard}>
                                        <Card.Content>
                                            <View style={styles.missionHeader}>
                                                <View style={[styles.categoryBadge, { backgroundColor: getCategoryColor(mission.category) + '20' }]}>
                                                    <Ionicons 
                                                        name={getCategoryIcon(mission.category)} 
                                                        size={14} 
                                                        color={getCategoryColor(mission.category)} 
                                                    />
                                                    <Text style={[styles.categoryText, { color: getCategoryColor(mission.category) }]}>
                                                        {mission.category?.toUpperCase() || 'ENERGY'}
                                                    </Text>
                                                </View>
                                                <View style={styles.activeBadge}>
                                                    <Ionicons name="time" size={12} color="#F59E0B" />
                                                    <Text style={styles.activeBadgeText}>{mission.time_remaining}</Text>
                                                </View>
                                            </View>

                                            <Text style={styles.missionTitle}>{mission.title}</Text>
                                            <Text style={styles.missionDescription}>{mission.description}</Text>

                                            <View style={styles.progressContainer}>
                                                <View style={[styles.progressBar, { width: `${mission.progress || 0}%` }]} />
                                            </View>
                                            <Text style={styles.progressText}>{mission.progress || 0}% complete</Text>

                                            <View style={styles.detailsRow}>
                                                <View style={styles.detailItem}>
                                                    <Ionicons name="calendar" size={14} color="#6B7280" />
                                                    <Text style={styles.detailText}>Started {formatTime(mission.accepted_at)}</Text>
                                                </View>
                                            </View>

                                            <View style={styles.rewardsRow}>
                                                <View style={styles.rewardItem}>
                                                    <Ionicons name="trophy" size={16} color="#F59E0B" />
                                                    <Text style={styles.rewardText}>{mission.tokens_reward} tokens</Text>
                                                </View>
                                            </View>

                                            <View style={styles.activeActions}>
                                                <TouchableOpacity
                                                    style={styles.completeActiveButton}
                                                    onPress={() => handleCompleteMission(mission)}
                                                >
                                                    <Text style={styles.completeActiveButtonText}>Mark Complete</Text>
                                                </TouchableOpacity>
                                                <TouchableOpacity
                                                    style={styles.cancelButton}
                                                    onPress={() => cancelMission(mission)}
                                                >
                                                    <Ionicons name="close" size={20} color="#EF4444" />
                                                </TouchableOpacity>
                                            </View>
                                        </Card.Content>
                                    </Card>
                                ))}

                                {activeMissions.length === 0 && (
                                    <Card style={styles.emptyCard}>
                                        <Card.Content>
                                            <Ionicons name="play-circle" size={48} color="#D1D5DB" />
                                            <Text style={styles.emptyTitle}>No Active Missions</Text>
                                            <Text style={styles.emptyText}>
                                                Accept an ML-recommended mission to get started!
                                            </Text>
                                            <TouchableOpacity
                                                style={styles.goToRecommendedButton}
                                                onPress={() => setActiveTab('recommended')}
                                            >
                                                <Text style={styles.goToRecommendedText}>View ML Recommendations</Text>
                                            </TouchableOpacity>
                                        </Card.Content>
                                    </Card>
                                )}
                            </>
                        )}

                        {/* COMPLETED TAB */}
                        {activeTab === 'completed' && (
                            <>
                                {completedMissions.map((mission, index) => (
                                    <Card key={mission.id || index} style={[styles.missionCard, styles.completedCard]}>
                                        <Card.Content>
                                            <View style={styles.missionHeader}>
                                                <View style={[styles.categoryBadge, { backgroundColor: getCategoryColor(mission.category) + '20' }]}>
                                                    <Ionicons 
                                                        name={getCategoryIcon(mission.category)} 
                                                        size={14} 
                                                        color={getCategoryColor(mission.category)} 
                                                    />
                                                    <Text style={[styles.categoryText, { color: getCategoryColor(mission.category) }]}>
                                                        {mission.category?.toUpperCase() || 'ENERGY'}
                                                    </Text>
                                                </View>
                                                <View style={styles.completedBadge}>
                                                    <Ionicons name="checkmark-circle" size={14} color="#10B981" />
                                                    <Text style={styles.completedBadgeText}>Completed</Text>
                                                </View>
                                            </View>

                                            <Text style={styles.missionTitle}>{mission.title}</Text>
                                            <Text style={styles.missionDescription}>{mission.description}</Text>

                                            <View style={styles.completedStats}>
                                                <View style={styles.completedStat}>
                                                    <Ionicons name="trophy" size={16} color="#F59E0B" />
                                                    <Text style={styles.completedStatText}>+{mission.tokens_earned} tokens</Text>
                                                </View>
                                                <View style={styles.completedStat}>
                                                    <Ionicons name="leaf" size={16} color="#10B981" />
                                                    <Text style={styles.completedStatText}>{mission.co2_saved}kg CO₂ saved</Text>
                                                </View>
                                            </View>

                                            <Text style={styles.completedTime}>
                                                Completed {formatTime(mission.completed_at)}
                                            </Text>
                                        </Card.Content>
                                    </Card>
                                ))}

                                {completedMissions.length === 0 && (
                                    <Card style={styles.emptyCard}>
                                        <Card.Content>
                                            <Ionicons name="trophy-outline" size={48} color="#D1D5DB" />
                                            <Text style={styles.emptyTitle}>No Completed Missions</Text>
                                            <Text style={styles.emptyText}>
                                                Complete your first ML-recommended mission to see it here!
                                            </Text>
                                        </Card.Content>
                                    </Card>
                                )}
                            </>
                        )}
                    </>
                )}

                {/* Footer - shows ML info when working */}
                {!mlError && (
                    <View style={styles.footer}>
                        <Ionicons name="brain" size={16} color="#9CA3AF" />
                        <Text style={styles.footerText}>
                            Powered by LightGBM · 73.5% accuracy
                        </Text>
                    </View>
                )}
            </ScrollView>

            {/* Completion Verification Modal */}
            <Modal
                animationType="slide"
                transparent={true}
                visible={modalVisible}
                onRequestClose={() => setModalVisible(false)}
            >
                <View style={styles.modalOverlay}>
                    <View style={styles.modalContent}>
                        <View style={styles.modalHeader}>
                            <Ionicons name="checkmark-circle" size={40} color="#10B981" />
                            <Text style={styles.modalTitle}>Complete Mission</Text>
                        </View>

                        {selectedMission && (
                            <>
                                <Text style={styles.modalMissionTitle}>{selectedMission.title}</Text>
                                <Text style={styles.modalText}>
                                    Did you complete this ML-recommended mission? You'll earn:
                                </Text>

                                <View style={styles.modalRewards}>
                                    <View style={styles.modalReward}>
                                        <Ionicons name="trophy" size={20} color="#F59E0B" />
                                        <Text style={styles.modalRewardText}>{selectedMission.tokens_reward} tokens</Text>
                                    </View>
                                    <View style={styles.modalReward}>
                                        <Ionicons name="leaf" size={20} color="#10B981" />
                                        <Text style={styles.modalRewardText}>{selectedMission.savings_kg_co2}kg CO₂ saved</Text>
                                    </View>
                                </View>

                                <View style={styles.modalButtons}>
                                    <TouchableOpacity
                                        style={styles.modalCancelButton}
                                        onPress={() => setModalVisible(false)}
                                    >
                                        <Text style={styles.modalCancelText}>Not Yet</Text>
                                    </TouchableOpacity>
                                    <TouchableOpacity
                                        style={styles.modalConfirmButton}
                                        onPress={confirmCompletion}
                                    >
                                        <Text style={styles.modalConfirmText}>Yes, Complete!</Text>
                                    </TouchableOpacity>
                                </View>
                            </>
                        )}
                    </View>
                </View>
            </Modal>
        </>
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
        alignItems: 'center',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
    },
    mlBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 20,
    },
    mlBadgeText: {
        color: 'white',
        fontSize: 12,
        fontWeight: '600',
        marginLeft: 4,
    },
    subtitle: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
        marginTop: 4,
    },
    errorCard: {
        margin: 16,
        padding: 20,
        backgroundColor: '#FEE2E2',
        borderWidth: 1,
        borderColor: '#EF4444',
        borderRadius: 12,
        alignItems: 'center',
    },
    errorTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#991B1B',
        marginTop: 12,
        marginBottom: 8,
    },
    errorText: {
        fontSize: 14,
        color: '#B91C1C',
        textAlign: 'center',
        marginBottom: 8,
    },
    errorSubtext: {
        fontSize: 12,
        color: '#92400E',
        textAlign: 'center',
        marginBottom: 16,
    },
    retryButton: {
        backgroundColor: '#EF4444',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 8,
    },
    retryButtonText: {
        color: 'white',
        fontWeight: '600',
    },
    tabContainer: {
        flexDirection: 'row',
        backgroundColor: 'white',
        paddingVertical: 12,
        paddingHorizontal: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#E5E7EB',
    },
    tab: {
        flex: 1,
        paddingVertical: 8,
        alignItems: 'center',
        borderRadius: 20,
        marginHorizontal: 4,
    },
    activeTab: {
        backgroundColor: '#10B981',
    },
    tabText: {
        fontSize: 13,
        fontWeight: '500',
        color: '#6B7280',
    },
    activeTabText: {
        color: 'white',
    },
    missionCard: {
        marginHorizontal: 16,
        marginVertical: 8,
        borderRadius: 12,
    },
    completedCard: {
        backgroundColor: '#F9FAFB',
        borderWidth: 1,
        borderColor: '#E5E7EB',
    },
    missionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    categoryBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 16,
    },
    categoryText: {
        fontSize: 11,
        fontWeight: '600',
        marginLeft: 6,
    },
    scoreBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#D1FAE5',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 16,
    },
    scoreText: {
        fontSize: 11,
        fontWeight: '600',
        color: '#065F46',
        marginLeft: 4,
    },
    activeBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#FEF3C7',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 16,
    },
    activeBadgeText: {
        fontSize: 11,
        fontWeight: '600',
        color: '#92400E',
        marginLeft: 4,
    },
    completedBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#D1FAE5',
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 16,
    },
    completedBadgeText: {
        fontSize: 11,
        fontWeight: '600',
        color: '#065F46',
        marginLeft: 4,
    },
    missionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
        marginBottom: 4,
    },
    missionDescription: {
        fontSize: 13,
        color: '#6B7280',
        marginBottom: 12,
        lineHeight: 18,
    },
    detailsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    detailItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginRight: 16,
    },
    detailText: {
        fontSize: 12,
        color: '#6B7280',
        marginLeft: 4,
    },
    rewardsRow: {
        flexDirection: 'row',
        marginBottom: 16,
        gap: 12,
    },
    rewardItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#F3F4F6',
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: 8,
    },
    rewardText: {
        fontSize: 12,
        fontWeight: '500',
        color: '#374151',
        marginLeft: 6,
    },
    acceptButton: {
        backgroundColor: '#10B981',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 14,
        borderRadius: 8,
        marginBottom: 12,
    },
    acceptButtonText: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
        marginRight: 8,
    },
    confidenceContainer: {
        marginTop: 8,
    },
    confidenceLabel: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 4,
    },
    confidenceText: {
        fontSize: 11,
        color: '#6B7280',
    },
    confidenceValue: {
        fontSize: 11,
        fontWeight: '600',
        color: '#10B981',
    },
    confidenceBar: {
        height: 4,
        backgroundColor: '#E5E7EB',
        borderRadius: 2,
        overflow: 'hidden',
    },
    confidenceFill: {
        height: '100%',
        backgroundColor: '#10B981',
    },
    progressContainer: {
        height: 6,
        backgroundColor: '#E5E7EB',
        borderRadius: 3,
        marginBottom: 6,
        overflow: 'hidden',
    },
    progressBar: {
        height: '100%',
        backgroundColor: '#10B981',
    },
    progressText: {
        fontSize: 11,
        color: '#6B7280',
        marginBottom: 12,
    },
    activeActions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    completeActiveButton: {
        flex: 1,
        backgroundColor: '#10B981',
        padding: 12,
        borderRadius: 8,
        alignItems: 'center',
    },
    completeActiveButtonText: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
    },
    cancelButton: {
        width: 44,
        height: 44,
        borderRadius: 8,
        backgroundColor: '#FEE2E2',
        justifyContent: 'center',
        alignItems: 'center',
    },
    completedStats: {
        flexDirection: 'row',
        marginBottom: 8,
        gap: 16,
    },
    completedStat: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    completedStatText: {
        fontSize: 13,
        fontWeight: '500',
        color: '#374151',
        marginLeft: 6,
    },
    completedTime: {
        fontSize: 11,
        color: '#9CA3AF',
        marginTop: 8,
    },
    emptyCard: {
        margin: 16,
        padding: 20,
        alignItems: 'center',
        backgroundColor: 'white',
        borderRadius: 12,
    },
    emptyTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#111827',
        marginTop: 12,
        marginBottom: 8,
    },
    emptyText: {
        fontSize: 14,
        color: '#6B7280',
        textAlign: 'center',
        marginBottom: 16,
    },
    goToRecommendedButton: {
        backgroundColor: '#10B981',
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 8,
    },
    goToRecommendedText: {
        color: 'white',
        fontWeight: '600',
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
    },
    footerText: {
        fontSize: 12,
        color: '#9CA3AF',
        marginLeft: 6,
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    modalContent: {
        backgroundColor: 'white',
        borderRadius: 16,
        padding: 24,
        width: '80%',
        maxWidth: 340,
    },
    modalHeader: {
        alignItems: 'center',
        marginBottom: 20,
    },
    modalTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#111827',
        marginTop: 8,
    },
    modalMissionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#10B981',
        textAlign: 'center',
        marginBottom: 12,
    },
    modalText: {
        fontSize: 14,
        color: '#6B7280',
        textAlign: 'center',
        marginBottom: 16,
    },
    modalRewards: {
        backgroundColor: '#F3F4F6',
        borderRadius: 8,
        padding: 16,
        marginBottom: 20,
    },
    modalReward: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        marginVertical: 4,
    },
    modalRewardText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#111827',
        marginLeft: 8,
    },
    modalButtons: {
        flexDirection: 'row',
        gap: 12,
    },
    modalCancelButton: {
        flex: 1,
        padding: 14,
        borderRadius: 8,
        backgroundColor: '#F3F4F6',
        alignItems: 'center',
    },
    modalCancelText: {
        color: '#6B7280',
        fontSize: 14,
        fontWeight: '600',
    },
    modalConfirmButton: {
        flex: 1,
        padding: 14,
        borderRadius: 8,
        backgroundColor: '#10B981',
        alignItems: 'center',
    },
    modalConfirmText: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
    },
});

export default RecommendationsScreen;
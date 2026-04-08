// CarbonLifeApp/App.js
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { AuthProvider, useAuth } from './src/context/AuthContext';

// Import screens
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import RecommendationsScreen from './src/screens/RecommendationsScreen';
import RealtimeRecommendationsScreen from './src/screens/RealtimeRecommendationsScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

/**
 * Main Tab Navigator (shown when logged in)
 * Contains all the main screens of the app
 */
function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          if (route.name === 'Home') {
            iconName = focused ? 'home' : 'home-outline';
          } else if (route.name === 'Dashboard') {
            iconName = focused ? 'speedometer' : 'speedometer-outline';
          } else if (route.name === 'Recommendations') {
            iconName = focused ? 'bulb' : 'bulb-outline';
          } else if (route.name === 'LiveInsights') {
            iconName = focused ? 'analytics' : 'analytics-outline';
          } else if (route.name === 'Profile') {
            iconName = focused ? 'person' : 'person-outline';
          }
          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#10B981',
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: '#10B981',
        },
        headerTintColor: 'white',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      })}
    >
      <Tab.Screen 
        name="Home" 
        component={HomeScreen} 
        options={{ title: 'CarbonLife' }}
      />
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardScreen} 
        options={{ title: 'Energy' }}
      />
      <Tab.Screen 
        name="Recommendations" 
        component={RecommendationsScreen} 
        options={{ title: 'Missions' }}
      />
      <Tab.Screen 
        name="LiveInsights" 
        component={RealtimeRecommendationsScreen} 
        options={{ title: 'Live Insights' }}
      />
      <Tab.Screen 
        name="Profile" 
        component={ProfileScreen} 
        options={{ title: 'Profile' }}
      />
    </Tab.Navigator>
  );
}

/**
 * Root Navigator - switches between Auth and Main based on login state
 */
function AppNavigator() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </>
      ) : (
        <Stack.Screen name="Main" component={MainTabs} />
      )}
    </Stack.Navigator>
  );
}

/**
 * Root App component
 */
export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
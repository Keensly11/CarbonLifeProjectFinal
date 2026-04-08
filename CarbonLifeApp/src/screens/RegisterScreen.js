// CarbonLifeApp/src/screens/RegisterScreen.js
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useAuth } from '../context/AuthContext';

const RegisterScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    fullName: '',
    emirate: 'Dubai',
    homeType: 'Villa',
    bedrooms: '3',
    vehicleType: 'SUV',
    vehicleFuel: 'Petrol'
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const handleRegister = async () => {
    // Basic validation
    if (!formData.email || !formData.username || !formData.password) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }

    setLoading(true);
    
    // Format data for API
    const userData = {
      email: formData.email,
      username: formData.username,
      password: formData.password,
      full_name: formData.fullName || null,
      emirate: formData.emirate,
      home_type: formData.homeType,
      bedrooms: parseInt(formData.bedrooms),
      vehicle_type: formData.vehicleType,
      vehicle_fuel: formData.vehicleFuel
    };

    const result = await register(userData);
    setLoading(false);

    if (result.success) {
      Alert.alert(
        'Success',
        'Registration successful! Please login.',
        [{ text: 'OK', onPress: () => navigation.goBack() }]
      );
    } else {
      Alert.alert('Registration Failed', result.error);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join CarbonLife UAE</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.sectionTitle}>Account Information</Text>
          
          <Text style={styles.label}>Email *</Text>
          <TextInput
            style={styles.input}
            placeholder="your@email.com"
            value={formData.email}
            onChangeText={(text) => setFormData({...formData, email: text})}
            autoCapitalize="none"
            keyboardType="email-address"
          />

          <Text style={styles.label}>Username *</Text>
          <TextInput
            style={styles.input}
            placeholder="Choose a username"
            value={formData.username}
            onChangeText={(text) => setFormData({...formData, username: text})}
            autoCapitalize="none"
          />

          <Text style={styles.label}>Password *</Text>
          <TextInput
            style={styles.input}
            placeholder="Choose a password"
            value={formData.password}
            onChangeText={(text) => setFormData({...formData, password: text})}
            secureTextEntry
          />

          <Text style={styles.label}>Full Name (Optional)</Text>
          <TextInput
            style={styles.input}
            placeholder="Your full name"
            value={formData.fullName}
            onChangeText={(text) => setFormData({...formData, fullName: text})}
          />

          <Text style={styles.sectionTitle}>UAE Household Details</Text>

          <Text style={styles.label}>Emirate</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.emirate}
              onValueChange={(value) => setFormData({...formData, emirate: value})}
            >
              <Picker.Item label="Dubai" value="Dubai" />
              <Picker.Item label="Abu Dhabi" value="Abu Dhabi" />
              <Picker.Item label="Sharjah" value="Sharjah" />
              <Picker.Item label="Ajman" value="Ajman" />
              <Picker.Item label="RAK" value="RAK" />
            </Picker>
          </View>

          <Text style={styles.label}>Home Type</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.homeType}
              onValueChange={(value) => setFormData({...formData, homeType: value})}
            >
              <Picker.Item label="Villa" value="Villa" />
              <Picker.Item label="Apartment" value="Apartment" />
              <Picker.Item label="Townhouse" value="Townhouse" />
            </Picker>
          </View>

          <Text style={styles.label}>Number of Bedrooms</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.bedrooms}
              onValueChange={(value) => setFormData({...formData, bedrooms: value})}
            >
              <Picker.Item label="1" value="1" />
              <Picker.Item label="2" value="2" />
              <Picker.Item label="3" value="3" />
              <Picker.Item label="4" value="4" />
              <Picker.Item label="5+" value="5" />
            </Picker>
          </View>

          <Text style={styles.sectionTitle}>Transportation</Text>

          <Text style={styles.label}>Vehicle Type</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.vehicleType}
              onValueChange={(value) => setFormData({...formData, vehicleType: value})}
            >
              <Picker.Item label="SUV" value="SUV" />
              <Picker.Item label="Sedan" value="Sedan" />
              <Picker.Item label="Sports Car" value="Sports" />
              <Picker.Item label="Electric" value="Electric" />
              <Picker.Item label="No Vehicle" value="None" />
            </Picker>
          </View>

          <Text style={styles.label}>Fuel Type</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={formData.vehicleFuel}
              onValueChange={(value) => setFormData({...formData, vehicleFuel: value})}
            >
              <Picker.Item label="Petrol" value="Petrol" />
              <Picker.Item label="Diesel" value="Diesel" />
              <Picker.Item label="Hybrid" value="Hybrid" />
              <Picker.Item label="Electric" value="Electric" />
              <Picker.Item label="N/A" value="None" />
            </Picker>
          </View>

          <TouchableOpacity
            style={styles.registerButton}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.registerButtonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>Already have an account? </Text>
            <TouchableOpacity onPress={() => navigation.goBack()}>
              <Text style={styles.loginLink}>Login</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    backgroundColor: '#10B981',
    padding: 30,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    marginTop: 4,
  },
  form: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginTop: 20,
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    fontSize: 16,
  },
  pickerContainer: {
    backgroundColor: 'white',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    overflow: 'hidden',
  },
  registerButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 30,
    marginBottom: 20,
  },
  registerButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 30,
  },
  loginText: {
    color: '#6B7280',
    fontSize: 14,
  },
  loginLink: {
    color: '#10B981',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default RegisterScreen;
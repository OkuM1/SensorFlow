#!/usr/bin/env python3
"""
SensorFlow - Machine Learning Anomaly Detection
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorAnomalyDetector:
    """Advanced ML-based anomaly detection for sensor data"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.sensor_stats = {}
        
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for anomaly detection"""
        
        features = data.copy()
        
        # Time-based features
        features['hour'] = pd.to_datetime(features['timestamp']).dt.hour
        features['day_of_week'] = pd.to_datetime(features['timestamp']).dt.dayofweek
        features['month'] = pd.to_datetime(features['timestamp']).dt.month
        
        # Rolling statistics (per sensor)
        for sensor_id in features['sensor_id'].unique():
            mask = features['sensor_id'] == sensor_id
            sensor_data = features[mask].sort_values('timestamp')
            
            # Rolling window statistics
            features.loc[mask, 'rolling_mean_5'] = sensor_data['value'].rolling(5, min_periods=1).mean()
            features.loc[mask, 'rolling_std_5'] = sensor_data['value'].rolling(5, min_periods=1).std()
            features.loc[mask, 'rolling_mean_20'] = sensor_data['value'].rolling(20, min_periods=1).mean()
            features.loc[mask, 'rolling_std_20'] = sensor_data['value'].rolling(20, min_periods=1).std()
            
            # Rate of change
            features.loc[mask, 'value_diff'] = sensor_data['value'].diff()
            features.loc[mask, 'value_diff_abs'] = sensor_data['value'].diff().abs()
            
        # Deviation from rolling mean
        features['deviation_from_mean_5'] = np.abs(features['value'] - features['rolling_mean_5'])
        features['deviation_from_mean_20'] = np.abs(features['value'] - features['rolling_mean_20'])
        
        # Z-score features
        features['z_score_5'] = (features['value'] - features['rolling_mean_5']) / (features['rolling_std_5'] + 1e-6)
        features['z_score_20'] = (features['value'] - features['rolling_mean_20']) / (features['rolling_std_20'] + 1e-6)
        
        # Fill NaN values
        features = features.fillna(method='bfill').fillna(method='ffill').fillna(0)
        
        return features
    
    def train_isolation_forest(self, sensor_type: str, training_data: pd.DataFrame):
        """Train Isolation Forest model for a specific sensor type"""
        
        logger.info(f"Training Isolation Forest for {sensor_type}")
        
        # Prepare features
        features = self.prepare_features(training_data)
        
        # Select numerical features for training
        feature_columns = [
            'value', 'hour', 'day_of_week', 'month',
            'rolling_mean_5', 'rolling_std_5', 'rolling_mean_20', 'rolling_std_20',
            'value_diff', 'value_diff_abs', 'deviation_from_mean_5', 'deviation_from_mean_20',
            'z_score_5', 'z_score_20'
        ]
        
        X = features[feature_columns]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train Isolation Forest
        model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        
        model.fit(X_scaled)
        
        # Store model and scaler
        self.models[f"{sensor_type}_isolation"] = model
        self.scalers[f"{sensor_type}_isolation"] = scaler
        
        # Calculate performance on training data
        predictions = model.predict(X_scaled)
        anomaly_ratio = np.sum(predictions == -1) / len(predictions)
        logger.info(f"Isolation Forest for {sensor_type}: {anomaly_ratio:.2%} anomalies detected")
        
        return model, scaler
    
    def train_dbscan(self, sensor_type: str, training_data: pd.DataFrame):
        """Train DBSCAN clustering model for anomaly detection"""
        
        logger.info(f"Training DBSCAN for {sensor_type}")
        
        features = self.prepare_features(training_data)
        
        feature_columns = ['value', 'rolling_mean_5', 'rolling_std_5', 'value_diff']
        X = features[feature_columns]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train DBSCAN
        model = DBSCAN(eps=0.5, min_samples=5)
        clusters = model.fit_predict(X_scaled)
        
        # Points with cluster label -1 are considered anomalies
        anomaly_ratio = np.sum(clusters == -1) / len(clusters)
        logger.info(f"DBSCAN for {sensor_type}: {anomaly_ratio:.2%} anomalies detected")
        
        # Store model and scaler
        self.models[f"{sensor_type}_dbscan"] = model
        self.scalers[f"{sensor_type}_dbscan"] = scaler
        
        return model, scaler
    
    def predict_anomalies(self, sensor_type: str, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Predict anomalies using trained models"""
        
        features = self.prepare_features(data)
        predictions = {}
        
        # Isolation Forest predictions
        if f"{sensor_type}_isolation" in self.models:
            feature_columns = [
                'value', 'hour', 'day_of_week', 'month',
                'rolling_mean_5', 'rolling_std_5', 'rolling_mean_20', 'rolling_std_20',
                'value_diff', 'value_diff_abs', 'deviation_from_mean_5', 'deviation_from_mean_20',
                'z_score_5', 'z_score_20'
            ]
            
            X = features[feature_columns]
            scaler = self.scalers[f"{sensor_type}_isolation"]
            model = self.models[f"{sensor_type}_isolation"]
            
            X_scaled = scaler.transform(X)
            isolation_pred = model.predict(X_scaled)
            isolation_scores = model.decision_function(X_scaled)
            
            predictions['isolation_forest'] = {
                'predictions': isolation_pred,
                'scores': isolation_scores,
                'anomalies': isolation_pred == -1
            }
        
        # DBSCAN predictions
        if f"{sensor_type}_dbscan" in self.models:
            feature_columns = ['value', 'rolling_mean_5', 'rolling_std_5', 'value_diff']
            X = features[feature_columns]
            scaler = self.scalers[f"{sensor_type}_dbscan"]
            model = self.models[f"{sensor_type}_dbscan"]
            
            X_scaled = scaler.transform(X)
            dbscan_pred = model.fit_predict(X_scaled)
            
            predictions['dbscan'] = {
                'predictions': dbscan_pred,
                'anomalies': dbscan_pred == -1
            }
        
        return predictions
    
    def save_models(self, filepath: str):
        """Save trained models to disk"""
        
        models_data = {
            'models': self.models,
            'scalers': self.scalers,
            'sensor_stats': self.sensor_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        joblib.dump(models_data, filepath)
        logger.info(f"Models saved to {filepath}")
    
    def load_models(self, filepath: str):
        """Load trained models from disk"""
        
        models_data = joblib.load(filepath)
        
        self.models = models_data['models']
        self.scalers = models_data['scalers']
        self.sensor_stats = models_data.get('sensor_stats', {})
        
        logger.info(f"Models loaded from {filepath}")
        logger.info(f"Available models: {list(self.models.keys())}")

def main():
    """Example usage of the anomaly detection system"""
    
    # Initialize detector
    detector = SensorAnomalyDetector()
    
    # Example with sample data
    sample_data = pd.DataFrame({
        'sensor_id': ['TEMP_001'] * 1000,
        'sensor_type': ['temperature'] * 1000,
        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1T'),
        'value': np.random.normal(22, 2, 1000),  # Normal temperature data
        'location': ['Building-A'] * 1000
    })
    
    # Add some anomalies
    anomaly_indices = np.random.choice(1000, 50, replace=False)
    sample_data.loc[anomaly_indices, 'value'] += np.random.normal(10, 5, 50)
    
    # Train models
    detector.train_isolation_forest('temperature', sample_data)
    detector.train_dbscan('temperature', sample_data)
    
    # Test predictions
    predictions = detector.predict_anomalies('temperature', sample_data.tail(100))
    
    print("Anomaly Detection Results:")
    for model_name, results in predictions.items():
        anomaly_count = np.sum(results['anomalies'])
        print(f"{model_name}: {anomaly_count} anomalies detected")
    
    # Save models
    detector.save_models('models/anomaly_models.joblib')

if __name__ == "__main__":
    main()

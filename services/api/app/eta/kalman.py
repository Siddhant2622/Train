"""Kalman Filter ML Layer for ETA Smoothing.

This module implements a 1D Kalman Filter to smooth ETA predictions in real-time.
It takes the physics+ML predicted delay (measurement) and combines it with
the previous state to reduce jitter/noise in predictions.
"""

import logging
from datetime import timedelta
from app.eta.baseline import EtaResult

logger = logging.getLogger(__name__)

class KalmanFilter1D:
    def __init__(self, process_noise: float = 1.0, measurement_noise: float = 2.0):
        """
        Initialize the 1D Kalman filter.
        process_noise (Q): Variance of the true state evolution (how fast true delay changes).
        measurement_noise (R): Variance of the measurement (how noisy our ML prediction is).
        """
        self.Q = process_noise
        self.R = measurement_noise
        
        # State: [delay_min, variance]
        self.state_estimate = 0.0
        self.error_cov = 1.0
        self.initialized = False

    def update(self, measurement: float) -> tuple[float, float]:
        """
        Apply a Kalman filter update step.
        Returns: (smoothed_estimate, estimate_variance)
        """
        if not self.initialized:
            self.state_estimate = measurement
            self.error_cov = 1.0
            self.initialized = True
            return self.state_estimate, self.error_cov

        # Prediction step (assume state stays roughly the same, but uncertainty grows)
        pred_state = self.state_estimate
        pred_cov = self.error_cov + self.Q
        
        # Update step (incorporate the new measurement)
        kalman_gain = pred_cov / (pred_cov + self.R)
        self.state_estimate = pred_state + kalman_gain * (measurement - pred_state)
        self.error_cov = (1 - kalman_gain) * pred_cov
        
        return self.state_estimate, self.error_cov


# A simple in-memory store of filters per train+station to maintain state across pings
# In a real production system, this state would be persisted in Redis.
_filters: dict[str, KalmanFilter1D] = {}

def apply_kalman_filter(eta_result: EtaResult) -> EtaResult:
    """Smooths the ETA predictions using a Kalman filter."""
    
    train_key = eta_result.train_number
    
    for stop in eta_result.stops:
        # Unique key for tracking this specific stop's filter state
        filter_key = f"{train_key}_{stop.station_code}"
        
        if filter_key not in _filters:
            # Initialize with sensible defaults for train delays
            _filters[filter_key] = KalmanFilter1D(process_noise=1.5, measurement_noise=3.0)
            
        kf = _filters[filter_key]
        
        # The measurement is our current predicted delay at this stop
        measurement = stop.delay_at_stop_min
        
        # Apply filter
        smoothed_delay, variance = kf.update(measurement)
        
        # Calculate the difference to apply to the bounds
        diff = smoothed_delay - measurement
        
        stop.predicted_eta += timedelta(minutes=diff)
        stop.delay_at_stop_min = smoothed_delay
        
        # Widen/tighten the confidence bounds based on the Kalman variance
        # Standard deviation is sqrt(variance)
        std_dev = variance ** 0.5
        stop.lower_bound = stop.predicted_eta - timedelta(minutes=std_dev * 1.5)
        stop.upper_bound = stop.predicted_eta + timedelta(minutes=std_dev * 1.5)
        
        stop.explanation["kalman_smoothed"] = True
        stop.explanation["kalman_variance"] = round(variance, 2)
        stop.explanation["engine"] = "kalman_smoothed_v1"
        
    eta_result.model_version = "kalman_smoothed_v1"
    
    return eta_result

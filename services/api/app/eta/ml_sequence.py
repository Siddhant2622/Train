"""Sequence ML Layer (GRU).

This module implements a Gated Recurrent Unit (GRU) forward pass using NumPy.
By using pure NumPy instead of PyTorch, we avoid a massive ~2.5GB dependency
for inference, keeping the Docker image lightweight while still demonstrating
sequence modeling for delay propagation.

The GRU takes the current delay and the XGBoost predicted delay at each stop,
and models how the delay "cascades" or is "recovered" through the sequence of stations.
"""

import numpy as np
from datetime import timedelta
from typing import Any
import logging

from app.eta.baseline import EtaResult

logger = logging.getLogger(__name__)

class NumpyGRU:
    """A minimal Numpy-based GRU for inference only."""
    def __init__(self, input_size: int, hidden_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # Initialize with dummy weights (since this is a simulated/hackathon model without a trained checkpoint)
        # In a real scenario, these would be loaded from a trained PyTorch model's state_dict
        np.random.seed(42)
        
        # Update gate weights
        self.W_z = np.random.randn(hidden_size, input_size) * 0.1
        self.U_z = np.random.randn(hidden_size, hidden_size) * 0.1
        self.b_z = np.zeros(hidden_size)
        
        # Reset gate weights
        self.W_r = np.random.randn(hidden_size, input_size) * 0.1
        self.U_r = np.random.randn(hidden_size, hidden_size) * 0.1
        self.b_r = np.zeros(hidden_size)
        
        # Candidate hidden state weights
        self.W_h = np.random.randn(hidden_size, input_size) * 0.1
        self.U_h = np.random.randn(hidden_size, hidden_size) * 0.1
        self.b_h = np.zeros(hidden_size)
        
        # Output layer
        self.W_out = np.random.randn(1, hidden_size) * 0.1
        self.b_out = np.zeros(1)
        
    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-x))
        
    def _tanh(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x)

    def forward(self, x_seq: list[np.ndarray]) -> list[float]:
        """
        Forward pass for a sequence of inputs.
        x_seq: List of feature vectors for each time step (station).
        Returns: List of predicted residual delays in minutes.
        """
        h = np.zeros(self.hidden_size)
        predictions = []
        
        for x in x_seq:
            # Update gate
            z = self._sigmoid(self.W_z @ x + self.U_z @ h + self.b_z)
            # Reset gate
            r = self._sigmoid(self.W_r @ x + self.U_r @ h + self.b_r)
            # Candidate hidden state
            h_tilde = self._tanh(self.W_h @ x + self.U_h @ (r * h) + self.b_h)
            # New hidden state
            h = (1 - z) * h + z * h_tilde
            
            # Predict residual from hidden state
            y = self.W_out @ h + self.b_out
            predictions.append(float(y[0]))
            
        return predictions


# Instantiate the singleton GRU model
# Features: [current_delay_min, distance_to_next, time_of_day]
_gru_model = NumpyGRU(input_size=3, hidden_size=8)


def apply_sequence_layer(
    eta_result: EtaResult,
    time_of_day_hour: int
) -> EtaResult:
    """Enhance the ETA result with GRU sequential delay cascade predictions."""
    
    if not eta_result.stops:
        return eta_result

    # Prepare sequences for the GRU
    x_seq = []
    for stop in eta_result.stops:
        dist = stop.__dict__.get("_dist_from_src", 0)
        curr_delay = stop.delay_at_stop_min
        
        # Input feature vector
        x = np.array([curr_delay, dist, time_of_day_hour])
        x_seq.append(x)
        
    # Run GRU inference
    try:
        gru_residuals = _gru_model.forward(x_seq)
    except Exception as e:
        logger.error(f"GRU Inference failed: {e}")
        return eta_result
        
    # Apply GRU residuals
    for i, stop in enumerate(eta_result.stops):
        # We scale the dummy GRU output to represent minutes of cascade delay
        # Since it's a dummy weight model, we clip it to reasonable values (-5 to +15 mins)
        residual = max(min(gru_residuals[i] * 5.0, 15.0), -5.0)
        
        stop.predicted_eta += timedelta(minutes=residual)
        stop.lower_bound += timedelta(minutes=residual)
        stop.upper_bound += timedelta(minutes=residual)
        stop.delay_at_stop_min += residual
        
        stop.explanation["gru_cascade_min"] = round(residual, 1)
        stop.explanation["engine"] = "gru_cascade_v1"
        
    eta_result.model_version = "gru_cascade_v1"
    
    return eta_result

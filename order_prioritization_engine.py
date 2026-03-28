"""
Order Prioritization Engine for Fairdeal Quick Commerce

This is a scoring system I built to handle the problem: when you get
way more orders than you can deliver, how do you decide which ones to do first?

The approach is pretty straightforward - score each order based on what matters
to the business, then fulfill the highest-scoring ones.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class OrderPrioritizationEngine:
    """The main class that scores orders and makes fulfillment decisions."""
    
    def __init__(self, capacity_per_hour: int = 50):
        """Initialize the engine with how many orders we can handle per hour."""
        self.capacity_per_hour = capacity_per_hour
        
        # The weights I came up with after thinking about what actually matters
        # Order value drives revenue (25%), but retailer relationships matter too (20%)
        # Time is critical - urgency and fairness both get 20% combined
        # Distance costs money and time (15%)
        self.weights = {
            'order_value': 0.25,           # How much $$$ 
            'retailer_importance': 0.20,   # How valuable is this customer?
            'urgency_factor': 0.20,        # Is the deadline approaching?
            'distance_penalty': 0.15,      # Is it nearby or across the city?
            'frequency_bonus': 0.10,       # Do they order a lot?
            'fairness_boost': 0.10         # Have we ignored them lately?
        }
        
        # Different customer tiers have different delivery promises
        # Premium shops (big chains) get 2 hours, small shops get 8 hours
        self.sla_thresholds = {
            'premium': 2,    # Big retailers, we promised fast
            'standard': 4,   # Medium retailers
            'basic': 8       # Smaller shops, more flexible
        }
        
        # Distance affects logistics cost. I split into zones to make
        # penalties more realistic than a pure linear model
        self.distance_zones = {
            'local': (0, 5),      # Same area - cheap
            'nearby': (5, 15),    # Within city - normal cost
            'distant': (15, 30),  # Far side of city - expensive
            'far': (30, float('inf'))  # Outliers - very expensive
        }
    
    def engineer_features(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer additional features for order prioritization.
        
        Args:
            orders_df: Raw orders dataframe
            
        Returns:
            Enhanced dataframe with engineered features
        """
        df = orders_df.copy()
        
        # Convert order_time to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df['order_time']):
            df['order_time'] = pd.to_datetime(df['order_time'])
        
        # 1. Retailer Tier Classification
        df['retailer_tier'] = self._classify_retailer_tier(df)
        
        # 2. Urgency Score
        df['urgency_score'] = self._calculate_urgency_score(df)
        
        # 3. Distance Zone Classification
        df['distance_zone'] = self._classify_distance_zone(df)
        
        # 4. Normalized Order Value
        df['normalized_order_value'] = self._normalize_feature(df['order_value'])
        
        # 5. Retailer Importance Score
        df['retailer_importance'] = self._calculate_retailer_importance(df)
        
        # 6. Frequency Bonus
        df['frequency_bonus'] = self._calculate_frequency_bonus(df)
        
        # 7. Distance Penalty
        df['distance_penalty'] = self._calculate_distance_penalty(df)
        
        # 8. Time-based features
        df['hour_of_day'] = df['order_time'].dt.hour
        df['day_of_week'] = df['order_time'].dt.dayofweek
        df['is_peak_hour'] = df['hour_of_day'].apply(lambda x: 1 if x in [12, 13, 18, 19] else 0)
        
        # 9. Fairness tracking (orders fulfilled today per retailer)
        df['orders_fulfilled_today'] = self._get_orders_fulfilled_today(df)
        df['fairness_boost'] = self._calculate_fairness_boost(df)
        
        return df
    
    def _classify_retailer_tier(self, df: pd.DataFrame) -> pd.Series:
        """Classify retailers into tiers based on avg_basket_size and frequency."""
        def classify_tier(row):
            basket_size = row['avg_basket_size']
            frequency = row['historical_order_frequency']
            
            # Premium: High value AND high frequency
            if basket_size >= 5000 and frequency >= 10:
                return 'premium'
            # Standard: Medium value OR high frequency
            elif basket_size >= 2000 or frequency >= 5:
                return 'standard'
            else:
                return 'basic'
        
        return df.apply(classify_tier, axis=1)
    
    def _calculate_urgency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate urgency based on time elapsed and SLA requirements."""
        current_time = datetime.now()
        
        def urgency_score(row):
            time_elapsed = (current_time - row['order_time']).total_seconds() / 3600  # hours
            sla_threshold = self.sla_thresholds[row['retailer_tier']]
            
            # Urgency increases as we approach SLA deadline
            urgency = min(time_elapsed / sla_threshold, 1.0)
            
            # Exponential increase as we get closer to deadline
            return urgency ** 2
        
        return df.apply(urgency_score, axis=1)
    
    def _classify_distance_zone(self, df: pd.DataFrame) -> pd.Series:
        """Classify orders by distance zones for delivery efficiency."""
        def get_zone(distance):
            for zone, (min_dist, max_dist) in self.distance_zones.items():
                if min_dist <= distance < max_dist:
                    return zone
            return 'far'
        
        return df['distance'].apply(get_zone)
    
    def _normalize_feature(self, series: pd.Series) -> pd.Series:
        """Min-max normalize a feature to 0-1 range."""
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - min_val) / (max_val - min_val)
    
    def _calculate_retailer_importance(self, df: pd.DataFrame) -> pd.Series:
        """Calculate retailer importance based on tier and historical value."""
        tier_weights = {'premium': 1.0, 'standard': 0.7, 'basic': 0.4}
        
        # Combine tier weight with normalized basket size
        normalized_basket = self._normalize_feature(df['avg_basket_size'])
        
        return df['retailer_tier'].map(tier_weights) * (0.5 + 0.5 * normalized_basket)
    
    def _calculate_frequency_bonus(self, df: pd.DataFrame) -> pd.Series:
        """Calculate bonus for high-frequency retailers."""
        return self._normalize_feature(df['historical_order_frequency'])
    
    def _calculate_distance_penalty(self, df: pd.DataFrame) -> pd.Series:
        """Calculate penalty based on delivery distance."""
        # Higher distance = higher penalty
        normalized_distance = self._normalize_feature(df['distance'])
        
        # Zone-based multipliers for efficiency
        zone_multipliers = {
            'local': 0.1,    # Minimal penalty for local deliveries
            'nearby': 0.3,   # Low penalty for nearby
            'distant': 0.7,  # Moderate penalty
            'far': 1.0       # Maximum penalty
        }
        
        zone_penalty = df['distance_zone'].map(zone_multipliers)
        
        return normalized_distance * zone_penalty
    
    def _get_orders_fulfilled_today(self, df: pd.DataFrame) -> pd.Series:
        """Get count of orders fulfilled today per retailer (mock implementation)."""
        # In production, this would query the database
        # For demo, we'll simulate some retailers having orders already fulfilled
        np.random.seed(42)
        return df['retailer_id'].apply(lambda x: np.random.poisson(2))
    
    def _calculate_fairness_boost(self, df: pd.DataFrame) -> pd.Series:
        """Calculate fairness boost for retailers with few fulfilled orders today."""
        max_fulfilled = df['orders_fulfilled_today'].max()
        if max_fulfilled == 0:
            return pd.Series([0] * len(df), index=df.index)
        
        # Boost inversely proportional to orders fulfilled today
        return 1 - (df['orders_fulfilled_today'] / max_fulfilled)
    
    def calculate_priority_score(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate priority score for each order using the weighted formula:
        
        Priority Score = (w1 × normalized_order_value) + 
                        (w2 × retailer_importance) + 
                        (w3 × urgency_factor) - 
                        (w4 × distance_penalty) + 
                        (w5 × frequency_bonus) +
                        (w6 × fairness_boost)
        """
        # Engineer features first
        df = self.engineer_features(orders_df)
        
        # Calculate weighted priority score
        priority_score = (
            self.weights['order_value'] * df['normalized_order_value'] +
            self.weights['retailer_importance'] * df['retailer_importance'] +
            self.weights['urgency_factor'] * df['urgency_score'] +
            self.weights['frequency_bonus'] * df['frequency_bonus'] +
            self.weights['fairness_boost'] * df['fairness_boost'] -
            self.weights['distance_penalty'] * df['distance_penalty']
        )
        
        df['priority_score'] = priority_score
        
        return df
    
    def make_decisions(self, orders_df: pd.DataFrame, current_hour_capacity: int = None) -> pd.DataFrame:
        """
        Make fulfill/delay/reject decisions based on priority scores and constraints.
        
        Args:
            orders_df: Orders with priority scores
            current_hour_capacity: Override default hourly capacity
            
        Returns:
            DataFrame with decisions and additional metadata
        """
        if current_hour_capacity is None:
            current_hour_capacity = self.capacity_per_hour
        
        df = orders_df.copy()
        
        # Sort by priority score (descending)
        df = df.sort_values('priority_score', ascending=False).reset_index(drop=True)
        
        # Apply fairness constraints
        df = self._apply_fairness_constraints(df)
        
        # Make initial capacity-based decisions
        decisions = []
        fulfill_count = 0
        delay_count = 0
        max_delays = int(len(df) * 0.4)  # Allow up to 40% of orders to be delayed
        
        for idx, row in df.iterrows():
            if fulfill_count < current_hour_capacity:
                # Fulfill top orders
                decisions.append('Fulfill')
                fulfill_count += 1
            elif delay_count < max_delays:
                # Delay next set of orders (more lenient approach)
                decisions.append('Delay')
                delay_count += 1
            else:
                # Reject remaining orders
                decisions.append('Reject')
        
        df['decision'] = decisions
        
        # Add decision metadata
        df['fulfillment_rank'] = range(1, len(df) + 1)
        df['estimated_delay_hours'] = self._estimate_delay_hours(df)
        
        return df[['order_id', 'retailer_id', 'order_value', 'distance', 'retailer_tier', 
                  'priority_score', 'decision', 'fulfillment_rank', 'estimated_delay_hours']]
    
    def _apply_fairness_constraints(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply fairness constraints to ensure minimum orders per retailer and tier."""
        # Step 1: Ensure at least one premium retailer order in top positions if available
        premium_orders = df[df['retailer_tier'] == 'premium']
        if len(premium_orders) > 0:
            # Move top premium order to position 1 if not already there
            if df.iloc[0]['retailer_tier'] != 'premium':
                top_premium_idx = premium_orders.index[0]
                df = df.reset_index(drop=True)
                row_0 = df.loc[0].copy()
                row_premium = df.loc[top_premium_idx].copy()
                df.loc[0] = row_premium
                df.loc[top_premium_idx] = row_0
        
        # Step 2: Ensure each unique retailer gets at least 1 order opportunity
        # This guarantees fairness - no retailer is completely starved
        # We track which retailers have been picked and boost those not yet selected
        unique_retailers = df['retailer_id'].unique()
        retailers_boosted = set()
        
        # Mark retailers that are in top 40 (likely to be fulfilled)
        for idx in range(min(40, len(df))):
            retailers_boosted.add(df.iloc[idx]['retailer_id'])
        
        # For retailers not yet represented, find their best order and boost its priority
        for retailer_id in unique_retailers:
            if retailer_id not in retailers_boosted:
                # Find best order from this retailer
                retailer_orders = df[df['retailer_id'] == retailer_id]
                if len(retailer_orders) > 0:
                    best_order_idx = retailer_orders['priority_score'].idxmax()
                    # Give it a fairness boost by moving it up in ranking
                    # Find its current position and move it to just outside top 40
                    current_pos = df.index.get_loc(best_order_idx)
                    if current_pos > 38:  # Only if it's not already in top 40
                        target_pos = 38  # Place just before rejection zone
                        # Move this order up
                        order_to_move = df.loc[best_order_idx].copy()
                        df = df.drop(best_order_idx)
                        df = pd.concat([df.iloc[:target_pos], pd.DataFrame([order_to_move]), df.iloc[target_pos:]], ignore_index=True)
        
        return df
    
    def _meets_sla_requirements(self, order_row) -> bool:
        """Check if order meets SLA requirements for immediate fulfillment."""
        # For this demo, assume all orders meet SLA requirements
        # In production, this would check actual SLA constraints
        return True
    
    def _estimate_delay_hours(self, df: pd.DataFrame) -> pd.Series:
        """Estimate delay hours for non-fulfilled orders."""
        delay_hours = []
        
        for idx, row in df.iterrows():
            if row['decision'] == 'Fulfill':
                delay_hours.append(0)
            elif row['decision'] == 'Delay':
                # Estimate delay based on position in queue and capacity
                queue_position = max(0, row['fulfillment_rank'] - self.capacity_per_hour)
                estimated_delay = (queue_position // self.capacity_per_hour) + 1
                delay_hours.append(estimated_delay)
            else:  # Reject
                delay_hours.append(-1)  # -1 indicates rejection
        
        return pd.Series(delay_hours)

# Configuration and weight explanation
def explain_weight_selection():
    """
    Explain the rationale behind weight selection for the scoring formula.
    """
    explanation = """
    WEIGHT SELECTION RATIONALE:
    
    1. Order Value (25%): Primary revenue driver, but not overwhelming to allow other factors
    
    2. Retailer Importance (20%): Crucial for customer retention and long-term revenue
    
    3. Urgency Factor (20%): Essential for SLA compliance and customer satisfaction
    
    4. Distance Penalty (15%): Significant for operational efficiency and cost control
    
    5. Frequency Bonus (10%): Rewards loyal customers without overwhelming the system
    
    6. Fairness Boost (10%): Ensures smaller retailers aren't completely starved
    
    These weights balance short-term revenue optimization with long-term customer 
    relationship management and operational efficiency.
    
    WEIGHT TUNING:
    In production, these weights should be:
    - A/B tested for optimal business outcomes
    - Dynamically adjusted based on business conditions
    - Optimized using ML algorithms based on historical performance
    """
    return explanation
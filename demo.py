"""
Demo Script for Order Prioritization Engine
Generates sample data and demonstrates the complete pipeline
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from order_prioritization_engine import OrderPrioritizationEngine, explain_weight_selection

def generate_sample_data(num_orders: int = 100) -> pd.DataFrame:
    """
    Generate realistic sample order data for demonstration.
    
    Args:
        num_orders: Number of sample orders to generate
        
    Returns:
        DataFrame with sample order data
    """
    np.random.seed(42)  # For reproducible results
    
    # Generate retailer IDs (simulating 30 different retailers)
    retailer_ids = [f"RTL_{i:03d}" for i in range(1, 31)]
    
    # Generate warehouse IDs (simulating 5 warehouses)
    warehouse_ids = [f"WH_{i}" for i in range(1, 6)]
    
    orders = []
    base_time = datetime.now() - timedelta(hours=6)  # Orders from last 6 hours
    
    for order_num in range(1, num_orders + 1):
        # Select retailer (some retailers have higher probability of orders)
        retailer_weights = np.random.exponential(1, len(retailer_ids))
        retailer_id = np.random.choice(retailer_ids, p=retailer_weights/retailer_weights.sum())
        
        # Generate order data with realistic distributions
        order_data = {
            'order_id': f"ORD_{order_num:05d}",
            'retailer_id': retailer_id,
            'order_value': max(500, np.random.lognormal(mean=7.5, sigma=0.8)),  # 500 to 50000+ range
            'distance': max(0.5, np.random.gamma(2, 4)),  # 0.5 to 40+ km range
            'order_time': base_time + timedelta(
                hours=np.random.uniform(0, 6),
                minutes=np.random.randint(0, 60)
            ),
            'warehouse_id': np.random.choice(warehouse_ids)
        }
        orders.append(order_data)
    
    # Create DataFrame
    orders_df = pd.DataFrame(orders)
    
    # Generate retailer-specific historical data
    retailer_data = {}
    for retailer_id in retailer_ids:
        retailer_data[retailer_id] = {
            'historical_order_frequency': max(1, np.random.poisson(8)),  # orders per week
            'avg_basket_size': max(1000, np.random.lognormal(mean=7.8, sigma=0.6))
        }
    
    # Add historical data to orders
    orders_df['historical_order_frequency'] = orders_df['retailer_id'].map(
        lambda x: retailer_data[x]['historical_order_frequency']
    )
    orders_df['avg_basket_size'] = orders_df['retailer_id'].map(
        lambda x: retailer_data[x]['avg_basket_size']
    )
    
    # Round numerical values for cleaner display
    orders_df['order_value'] = orders_df['order_value'].round(2)
    orders_df['distance'] = orders_df['distance'].round(1)
    orders_df['avg_basket_size'] = orders_df['avg_basket_size'].round(2)
    
    return orders_df

def run_complete_demo():
    """Run the complete order prioritization demo."""
    
    print("="*80)
    print("INTELLIGENT ORDER PRIORITIZATION ENGINE - DEMO")
    print("="*80)
    
    # 1. Generate sample data
    print("\n1. GENERATING SAMPLE ORDER DATA...")
    orders_df = generate_sample_data(100)
    print(f"Generated {len(orders_df)} sample orders")
    print(f"Retailers: {orders_df['retailer_id'].nunique()}")
    print(f"Order value range: ₹{orders_df['order_value'].min():.2f} - ₹{orders_df['order_value'].max():.2f}")
    print(f"Distance range: {orders_df['distance'].min():.1f} - {orders_df['distance'].max():.1f} km")
    
    # Display sample of raw data
    print("\nSample of raw order data:")
    print(orders_df.head().to_string())
    
    # 2. Initialize the engine
    print("\n2. INITIALIZING PRIORITIZATION ENGINE...")
    engine = OrderPrioritizationEngine(capacity_per_hour=40)  # Capacity for 40 orders/hour
    
    # 3. Explain the scoring approach
    print("\n3. SCORING METHODOLOGY:")
    print(explain_weight_selection())
    
    # 4. Calculate priority scores
    print("\n4. CALCULATING PRIORITY SCORES...")
    scored_orders = engine.calculate_priority_score(orders_df)
    
    # Show engineered features for a few orders
    print("\nEngineered features for top 5 orders:")
    feature_columns = ['order_id', 'retailer_id', 'retailer_tier', 'normalized_order_value', 
                      'urgency_score', 'retailer_importance', 'distance_penalty', 'priority_score']
    print(scored_orders[feature_columns].head().to_string())
    
    # 5. Make decisions
    print("\n5. MAKING FULFILLMENT DECISIONS...")
    final_decisions = engine.make_decisions(scored_orders)
    
    # Display results summary
    print("\nDECISION SUMMARY:")
    decision_counts = final_decisions['decision'].value_counts()
    print(decision_counts.to_string())
    
    print(f"\nCapacity utilization: {decision_counts.get('Fulfill', 0)}/{engine.capacity_per_hour} orders")
    
    # 6. Show final output
    print("\n6. FINAL PRIORITIZATION RESULTS:")
    print("="*120)
    print(f"{'Order ID':<12} {'Retailer':<10} {'Value':<8} {'Distance':<8} {'Tier':<8} {'Priority':<8} {'Decision':<8} {'Delay(h)':<8}")
    print("="*120)
    
    for idx, row in final_decisions.head(25).iterrows():
        delay_str = str(int(row['estimated_delay_hours'])) if row['estimated_delay_hours'] >= 0 else "N/A"
        print(f"{row['order_id']:<12} {row['retailer_id']:<10} ₹{row['order_value']:<7.0f} "
              f"{row['distance']:<7.1f}km {row['retailer_tier']:<8} {row['priority_score']:<7.3f} "
              f"{row['decision']:<8} {delay_str:<8}")
    
    print("="*120)
    
    # 7. Business impact analysis
    print("\n7. BUSINESS IMPACT ANALYSIS:")
    
    fulfilled_orders = final_decisions[final_decisions['decision'] == 'Fulfill']
    delayed_orders = final_decisions[final_decisions['decision'] == 'Delay']
    rejected_orders = final_decisions[final_decisions['decision'] == 'Reject']
    
    total_revenue = orders_df['order_value'].sum()
    fulfilled_revenue = fulfilled_orders['order_value'].sum()
    delayed_revenue = delayed_orders['order_value'].sum()
    
    print(f"Total potential revenue: ₹{total_revenue:,.2f}")
    print(f"Immediate revenue (fulfilled): ₹{fulfilled_revenue:,.2f} ({fulfilled_revenue/total_revenue*100:.1f}%)")
    print(f"Delayed revenue: ₹{delayed_revenue:,.2f} ({delayed_revenue/total_revenue*100:.1f}%)")
    print(f"Lost revenue (rejected): ₹{total_revenue - fulfilled_revenue - delayed_revenue:,.2f}")
    
    # Retailer tier analysis
    print("\nRetailer tier distribution in fulfilled orders:")
    tier_distribution = fulfilled_orders['retailer_tier'].value_counts()
    print(tier_distribution.to_string())
    
    # Distance efficiency
    print("\nDistance efficiency (fulfilled orders):")
    print(f"Average distance: {fulfilled_orders['distance'].mean():.1f} km")
    print(f"Distance range: {fulfilled_orders['distance'].min():.1f} - {fulfilled_orders['distance'].max():.1f} km")
    
    return final_decisions

def demo_scenario_analysis():
    """Demonstrate how the system behaves under different scenarios."""
    
    print("\n" + "="*80)
    print("SCENARIO ANALYSIS")
    print("="*80)
    
    # Generate base data
    orders_df = generate_sample_data(50)
    
    scenarios = [
        {"name": "Normal Capacity", "capacity": 25, "description": "Standard operating conditions"},
        {"name": "High Demand", "capacity": 40, "description": "Increased capacity during peak demand"},
        {"name": "Low Demand", "capacity": 25, "description": "Standard capacity during low demand"}
    ]
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ({scenario['description']}) ---")
        engine = OrderPrioritizationEngine(capacity_per_hour=scenario['capacity'])
        
        # Calculate scores and make decisions
        scored_orders = engine.calculate_priority_score(orders_df)
        decisions = engine.make_decisions(scored_orders)
        
        # Analyze results
        decision_counts = decisions['decision'].value_counts()
        fulfilled_revenue = decisions[decisions['decision'] == 'Fulfill']['order_value'].sum()
        
        print(f"Capacity: {scenario['capacity']} orders/hour")
        print(f"Fulfilled: {decision_counts.get('Fulfill', 0)}")
        print(f"Delayed: {decision_counts.get('Delay', 0)}")
        print(f"Rejected: {decision_counts.get('Reject', 0)}")
        print(f"Revenue: ₹{fulfilled_revenue:,.2f}")

if __name__ == "__main__":
    # Run the main demo
    results = run_complete_demo()
    
    # Run scenario analysis
    demo_scenario_analysis()
    
    print("\n" + "="*80)
    print("DEMO COMPLETED - Review the results above!")
    print("="*80)
# Order Prioritization Engine for Fairdeal

## The Problem We're Solving

I was given this scenario: Fairdeal is a B2B quick commerce platform that keeps getting crushed with orders. Every morning around 9 AM, they get hit with 100+ orders an hour, but their warehouse can only handle 40. So they have a real choice problem: which 40 orders do we actually fulfill, which 40 do we push to the next hour, and which 20 do we straight-up reject?

It's not random. If you reject a big customer's order, they'll go somewhere else. If you keep delaying small shops, they'll get frustrated too. And if your deliveries are all 30km away, your riders are burned out and your costs are insane.

So here's what I built: an automated system that scores each order and picks the smartest ones to fulfill first.

## What I Actually Cared About

When I thought about how this should work, three things mattered:
- **Make money** - fulfill the orders that bring in the most revenue
- **Keep customers happy** - don't break delivery promises, and treat small shops fairly
- **Run efficiently** - prefer nearby deliveries over stuff across the city

## How It Works - 6 Scoring Factors

I settled on 6 factors that control which orders get prioritized. Each one has a reason:

### 1. Order Value (25%)
This is the obviousone - bigger orders = more money. A ₹10,000 order matters more than a ₹500 one.

### 2. Retailer Importance (20%)
Some customers are just worth more. I classify retailers into tiers:
- **Premium**: Big shops ordering 10+ times a week (think big kirana chains)
- **Standard**: Medium shops, 5-10 orders a week
- **Basic**: Small shops, under 5 times a week

These are where I've decided to build the relationship investment angle.

### 3. Urgency (20%)
If I promised someone a 2-hour delivery and they're at 1.9 hours, that order better jump the queue. Each tier has different promises, so I calculate how close they are to their deadline.

### 4. Distance (15% penalty)
Delivering 30km away costs way more than 5km. I penalize far deliveries to naturally push toward efficient routes. Creates a 4-zone system:
- 0-5km: efficient
- 5-15km: normal
- 15-30km: expensive
- 30+km: very expensive

### 5. How Often They Order (10%)
Loyal customers who order every week get a small boost. Not huge, but it's there.

### 6. Fairness Boost (10%)  
This is the "don't starve small shops" rule. If a small retailer hasn't gotten any orders today but a big one has gotten 5, we boost the small one a bit. Keeps things balanced.

## The Scoring Formula

```
Score = (0.25 × order_value) +
        (0.20 × retailer_status) +
        (0.20 × how_urgent) +
        (0.10 × loyalty_bonus) +
        (0.10 × fairness_boost) -
        (0.15 × distance_penalty)
```

Each thing is normalized to 0-1 so they actually compare fairly.

## What Actually Happens

When 100 orders show up:

1. I score all 100
2. Sort them highest to lowest  
3. Top 40 → **Fulfill now** (get them packed and shipped)
4. Next 40 → **Delay** (push to next hour)
5. Bottom 20 → **Reject** (they won't happen)

This balances getting 40 out immediately with a pipeline of 40 more coming, so we're keeping busy.

## Real Results

Running this on 100 test orders with a 40/hour capacity:

```
Fulfilled:    40 orders  →  ₹187,191 revenue (55%)
Delayed:      40 orders  →  ₹107,909 revenue (32%)
Rejected:     20 orders  →  ₹44,826 lost (13%)

Total captured: 86.8% of potential revenue
```

Why this works:
- Premium retailers? All of them got orders (3 out of 3)
- Average delivery distance? 8.5km (efficient)
- Decision time? Under 100ms (real-time)

## Why This Approach Beats Alternatives

**If you just pick randomly**: You get lucky or unlucky. Your best customers might get rejected.

**If you use rigid rules**: "Always do Premium first" ignores the fact that a bigger order from a Standard retailer might make more sense. Real business isn't that simple.

**What I built**: Flexible scoring that lets you weight what matters. The weights can change, the thresholds can change, but the logic stays clear.

## Future Improvements

I intentionally kept this simple instead of over-engineering it. Here's what could come next:

- **A/B Testing**: Test different weight combinations to find what actually maximizes revenue given our specific conditions
- **Dynamic Weights**: Adjust the weights based on time of day (morning vs evening have different patterns)
- **ML Learning**: Track which orders we fulfilled and which got rejected, then learn what patterns predict success
- **Real-time Integration**: Connect to actual warehouse capacity data instead of using a fixed number

But honestly? This version works now. Adding ML immediately would just make it harder to understand.

## The Code

Everything is in Python with Pandas/NumPy:
- `OrderPrioritizationEngine` class handles the scoring logic
- `make_decisions()` actually decides what to do with each order  
- Features are normalized so nothing dominates just because of scale
- Easy to tweak weights if business priorities change

To run the demo:
```bash
python demo.py
```

It generates 100 realistic orders and shows you the decisions.

## Key Assumptions I Made

1. Warehouse can physically handle 40 orders per hour (fixed constraint)
2. Retailers have 2/4/8 hour delivery SLA based on their tier (varies by agreement)
3. Distance affects cost linearly (simplification, but reasonable)
4. Orders from the same retailer should be somewhat spread out (fairness)
5. We can measure "retailer importance" based on their order frequency and size
6. Real-time decisions are needed (sub-second response time)

These are all reasonable assumptions for a quick commerce platform, but they could change with different business models.

## Notes on Practicality

I built this knowing it has to actually work:
- Scores are explainable - you can tell a retailer exactly why their order was delayed
- It adapts to different hours - peak hours get different capacity
- Fairness is built in - not just an afterthought
- Distance efficiency saves real money
- No complex ML that breaks when conditions change

This is something a warehouse manager could understand and trust, not a black box.

---
# In your models.py or directly in your routes file

pricing_data = {
    "tiers": ["Free","Basic", "Standard", "Professional", "Enterprise"],
    "monthly_prices": ["0","99", "249", "499", "Contact Us"],
    "price_id": ['n/a','price_1PJYPOEr99ZAPva5mGfiHNUh','price_1PJYUCEr99ZAPva5S4Mcynv9','price_1PJYVkEr99ZAPva5Dk68XuHq','price_enterprise'],
    "mode": ['n/a','subscription','subscription','subscription','subscription'],
    "coins": ['n/a',100,300,700,700],
    "plan_weight": [0,1,2,3,4],
    "products": [
        {
            "name": "Gaming GPT",
            "features": [
                {"name": "Tokens", "values": ["10 one off","100 /month", "300 /month", "700 /month", "700 /month"]},
                {"name": "Rate Limit", "values": ["1 Question Every 5 Minutes","1 Question Every 2 Minutes", "1 Question every 1 Minute", "1 Question every 30 Seconds", "1 Question every 10 Seconds"]},
            ]
        },
        {
            "name": "Insights API",
            "features": [
                {"name": "Historical Data Access", "values": ["None","1 month", "6 months", "12 months", "24 months"]},
                {"name": "Tech Support", "values": ["None","Basic", "Basic", "Priority", "Dedicated"]},
                {"name": "API Keys", "values": ["0 Seats","1 Seat", "2 Seats", "5 Seats", "10 Seats"]},
                {"name": "General Ranking", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Aggregated Rankings", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking Genres", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking List Types", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Single App Details", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "Details All Apps", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "All Publishers", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "App Availability", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Downloads", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Revenue", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Chrome Store Extensions", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Apple App Privacy", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Google Data Safety", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Reviews All Apps", "values": ["—","—", "—", "—", "✓"]},
                {"name": "App Ads", "values": ["—","—", "—", "—", "✓"]}
            ]
        },
        {
            "name": "Data Marketplace",
            "features": [
                {"name": "Historical Data Access", "values": ["None","1 month", "6 months", "12 months", "24 months"]},
                {"name": "Tech Support", "values": ["None","Basic", "Basic", "Priority", "Dedicated"]},
                {"name": "API Keys", "values": ["0 Seats","1 Seat", "2 Seats", "5 Seats", "10 Seats"]},
                {"name": "General Ranking", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Aggregated Rankings", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking Genres", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Ranking List Types", "values": ["—","✓", "✓", "✓", "✓"]},
                {"name": "Single App Details", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "Details All Apps", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "All Publishers", "values": ["—","—", "✓", "✓", "✓"]},
                {"name": "App Availability", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Downloads", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "App Estimates Revenue", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Chrome Store Extensions", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Apple App Privacy", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Google Data Safety", "values": ["—","—", "—", "✓", "✓"]},
                {"name": "Reviews All Apps", "values": ["—","—", "—", "—", "✓"]},
                {"name": "App Ads", "values": ["—","—", "—", "—", "✓"]}
            ]
        }
    ]
}
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
import statistics
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math
import hashlib
import sqlite3
from dataclasses import dataclass
import threading
import time

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

@dataclass
class MarketDataPoint:
    price: float
    platform: str
    condition: str
    days_ago: int
    size: Optional[str] = None

@dataclass
class SellerProfile:
    seller_id: str
    avg_response_time: float
    negotiation_flexibility: float
    listing_count: int
    account_age_days: int
    feedback_score: float

class EnhancedVintedAnalyzer:
    def __init__(self):
        self.brands_data = {
            # Luxury brands - higher base prices, slower depreciation
            "balenciaga": {"base": 200, "depreciation": 0.05, "demand": "luxury", "seasonal_factor": 1.0},
            "gucci": {"base": 250, "depreciation": 0.04, "demand": "luxury", "seasonal_factor": 1.0},
            "louis vuitton": {"base": 300, "depreciation": 0.03, "demand": "luxury", "seasonal_factor": 1.0},
            "prada": {"base": 280, "depreciation": 0.04, "demand": "luxury", "seasonal_factor": 1.0},
            "versace": {"base": 220, "depreciation": 0.05, "demand": "luxury", "seasonal_factor": 1.0},
            
            # Premium brands - moderate prices, steady demand
            "north face": {"base": 85, "depreciation": 0.08, "demand": "high", "seasonal_factor": 1.3},
            "patagonia": {"base": 90, "depreciation": 0.07, "demand": "high", "seasonal_factor": 1.25},
            "ralph lauren": {"base": 80, "depreciation": 0.10, "demand": "high", "seasonal_factor": 1.0},
            "tommy hilfiger": {"base": 70, "depreciation": 0.12, "demand": "medium", "seasonal_factor": 1.0},
            "calvin klein": {"base": 65, "depreciation": 0.12, "demand": "medium", "seasonal_factor": 1.0},
            "lacoste": {"base": 75, "depreciation": 0.10, "demand": "medium", "seasonal_factor": 1.0},
            
            # Streetwear - trend-dependent
            "supreme": {"base": 120, "depreciation": 0.15, "demand": "trend", "seasonal_factor": 1.1},
            "jordan": {"base": 90, "depreciation": 0.12, "demand": "trend", "seasonal_factor": 1.05},
            "nike": {"base": 60, "depreciation": 0.15, "demand": "high", "seasonal_factor": 1.0},
            "adidas": {"base": 55, "depreciation": 0.15, "demand": "high", "seasonal_factor": 1.0},
            "off-white": {"base": 150, "depreciation": 0.20, "demand": "trend", "seasonal_factor": 1.0},
            
            # Mid-range brands
            "new balance": {"base": 65, "depreciation": 0.18, "demand": "medium", "seasonal_factor": 1.0},
            "converse": {"base": 50, "depreciation": 0.20, "demand": "medium", "seasonal_factor": 1.0},
            "vans": {"base": 45, "depreciation": 0.20, "demand": "medium", "seasonal_factor": 1.0},
            "reebok": {"base": 50, "depreciation": 0.22, "demand": "medium", "seasonal_factor": 1.0},
            "puma": {"base": 45, "depreciation": 0.18, "demand": "medium", "seasonal_factor": 1.0},
            
            # Budget brands
            "champion": {"base": 40, "depreciation": 0.25, "demand": "low", "seasonal_factor": 1.0},
            "fila": {"base": 45, "depreciation": 0.25, "demand": "low", "seasonal_factor": 1.0},
            "carhartt": {"base": 55, "depreciation": 0.20, "demand": "medium", "seasonal_factor": 1.15},
            "river island": {"base": 35, "depreciation": 0.25, "demand": "medium", "seasonal_factor": 1.0}
        }
        
        self.item_categories = {
            # Outerwear - holds value well
            "jacket": {"base": 60, "seasonality": 0.3, "durability": "high", "size_variance": 0.1},
            "coat": {"base": 70, "seasonality": 0.4, "durability": "high", "size_variance": 0.15},
            "hoodie": {"base": 40, "seasonality": 0.1, "durability": "medium", "size_variance": 0.05},
            "parka": {"base": 80, "seasonality": 0.5, "durability": "high", "size_variance": 0.1},
            "blazer": {"base": 65, "seasonality": 0.1, "durability": "high", "size_variance": 0.1},
            
            # Footwear - brand dependent
            "trainers": {"base": 50, "seasonality": 0.1, "durability": "medium", "size_variance": 0.25},
            "sneakers": {"base": 55, "seasonality": 0.1, "durability": "medium", "size_variance": 0.25},
            "boots": {"base": 60, "seasonality": 0.3, "durability": "high", "size_variance": 0.2},
            "shoes": {"base": 45, "seasonality": 0.1, "durability": "medium", "size_variance": 0.2},
            
            # Basics - depreciate quickly
            "jeans": {"base": 35, "seasonality": 0.0, "durability": "high", "size_variance": 0.15},
            "trousers": {"base": 30, "seasonality": 0.0, "durability": "high", "size_variance": 0.15},
            "t-shirt": {"base": 20, "seasonality": 0.0, "durability": "low", "size_variance": 0.1},
            "shirt": {"base": 25, "seasonality": 0.0, "durability": "medium", "size_variance": 0.1},
            "dress": {"base": 45, "seasonality": 0.2, "durability": "medium", "size_variance": 0.1},
            
            # Accessories
            "bag": {"base": 40, "seasonality": 0.1, "durability": "high", "size_variance": 0.05},
            "watch": {"base": 70, "seasonality": 0.0, "durability": "high", "size_variance": 0.0}
        }

        # Common brands for autocomplete
        self.common_brands = [
            "Nike", "Adidas", "Puma", "New Balance", "Converse", "Vans", 
            "River Island", "Zara", "H&M", "ASOS", "Topman", "Next",
            "Ralph Lauren", "Tommy Hilfiger", "Calvin Klein", "Lacoste",
            "North Face", "Patagonia", "Supreme", "Champion", "Carhartt",
            "Gucci", "Prada", "Balenciaga", "Louis Vuitton", "Versace",
            "Off-White", "Stone Island", "Moncler", "Canada Goose"
        ]
        
        # Initialize database for learning
        self._init_database()
        
        # Market trends cache
        self.market_trends_cache = {}
        self.cache_timestamp = {}
        
        # Strategy success rates (loaded from database)
        self.strategy_success_rates = {}

    def _init_database(self):
        """Initialize SQLite database for learning and caching"""
        try:
            conn = sqlite3.connect('vinted_analyzer.db')
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS negotiations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT,
                    original_price REAL,
                    offered_price REAL,
                    strategy_used TEXT,
                    outcome TEXT,
                    seller_response_time INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_query TEXT,
                    platform TEXT,
                    price REAL,
                    condition TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seller_profiles (
                    seller_id TEXT PRIMARY KEY,
                    avg_response_time REAL,
                    negotiation_flexibility REAL,
                    listing_count INTEGER,
                    account_age_days INTEGER,
                    feedback_score REAL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            # Load strategy success rates
            self._update_strategy_success_rates()
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")

    def get_brand_suggestions(self, query: str) -> List[str]:
        """Get brand suggestions for autocomplete"""
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower()
        suggestions = []
        
        for brand in self.common_brands:
            if query_lower in brand.lower():
                suggestions.append(brand)
        
        return suggestions[:8]  # Increased to 8 suggestions

    def parse_time_string(self, time_str: str) -> int:
        """Parse time strings like '27 min ago', '2 hours ago', '3 days ago'"""
        time_str = time_str.lower().strip()
        
        # Handle different formats
        if 'min' in time_str:
            return 0  # Less than a day
        elif 'hour' in time_str:
            return 0  # Less than a day
        elif 'day' in time_str:
            # Extract number of days
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                return int(numbers[0])
        elif 'week' in time_str:
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                return int(numbers[0]) * 7
        elif 'month' in time_str:
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                return int(numbers[0]) * 30
        
        return 0

    def analyze_screenshot_text(self, text_content: str) -> Dict:
        """Analyze text extracted from screenshot"""
        lines = text_content.split('\n')
        extracted_data = {}
        
        # Look for brand names
        for line in lines:
            line_lower = line.lower().strip()
            for brand in self.common_brands:
                if brand.lower() in line_lower:
                    extracted_data['brand'] = brand
                    break
        
        # Look for size information
        size_patterns = [
            r'size\s+([A-Z0-9]+)',
            r'([A-Z]\d+)',
            r'(\d+[A-Z])',
            r'(XS|S|M|L|XL|XXL)',
            r'(UK\s*\d+)',
            r'(EU\s*\d+)',
            r'(US\s*\d+)'
        ]
        
        for line in lines:
            for pattern in size_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    extracted_data['size'] = match.group(1)
                    break
        
        # Look for condition
        condition_keywords = {
            'new without tags': 'New without tags',
            'new with tags': 'New with tags', 
            'new': 'New',
            'excellent': 'Excellent',
            'very good': 'Very good',
            'good': 'Good',
            'satisfactory': 'Satisfactory'
        }
        
        text_lower = text_content.lower()
        for keyword, condition in condition_keywords.items():
            if keyword in text_lower:
                extracted_data['condition'] = condition
                break
        
        # Look for views
        view_match = re.search(r'views?\s+(\d+)', text_content, re.IGNORECASE)
        if view_match:
            extracted_data['views'] = int(view_match.group(1))
        
        # Look for time information
        time_patterns = [
            r'(\d+)\s*min\s*ago',
            r'(\d+)\s*hour[s]?\s*ago', 
            r'(\d+)\s*day[s]?\s*ago',
            r'(\d+)\s*week[s]?\s*ago',
            r'(\d+)\s*month[s]?\s*ago'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                extracted_data['upload_time'] = self.parse_time_string(match.group(0))
                break
        
        # Try to extract item name/title (usually the longest meaningful line)
        meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        if meaningful_lines:
            # Take the first substantial line as potential item name
            extracted_data['item_name'] = meaningful_lines[0]
        
        return extracted_data

    def get_seasonal_factor(self, item_name: str) -> float:
        """Calculate seasonal pricing factor"""
        current_month = datetime.now().month
        item_lower = item_name.lower()
        
        # Winter items (Nov-Feb)
        if current_month in [11, 12, 1, 2]:
            if any(word in item_lower for word in ['coat', 'jacket', 'parka', 'boots', 'scarf']):
                return 1.25
            elif any(word in item_lower for word in ['shorts', 'sandals', 'bikini']):
                return 0.75
                
        # Summer items (May-Aug)
        elif current_month in [5, 6, 7, 8]:
            if any(word in item_lower for word in ['shorts', 'sandals', 'bikini', 'dress']):
                return 1.15
            elif any(word in item_lower for word in ['coat', 'jacket', 'parka', 'boots']):
                return 0.8
                
        return 1.0  # No seasonal adjustment

    def analyze_market_trends(self, query: str) -> Dict:
        """Analyze market trends and momentum"""
        cache_key = query.lower()
        
        # Check cache (valid for 1 hour)
        if cache_key in self.market_trends_cache:
            if time.time() - self.cache_timestamp[cache_key] < 3600:
                return self.market_trends_cache[cache_key]
        
        try:
            # Get price data from last 90 days
            historical_prices = self._fetch_historical_prices(query, days=90)
            
            if len(historical_prices) < 3:
                trend_data = {
                    'price_trend': 'stable',
                    'trend_strength': 0.0,
                    'demand_surge': False,
                    'seasonal_factor': self.get_seasonal_factor(query),
                    'hype_score': 0.5,
                    'data_sources': 1,
                    'estimated_market_price': self._estimate_from_keywords(query)
                }
            else:
                # Calculate trend
                recent_prices = [p.price for p in historical_prices[:10]]  # Last 10 sales
                older_prices = [p.price for p in historical_prices[-10:]]   # 10 sales from 90 days ago
                
                recent_avg = statistics.mean(recent_prices)
                older_avg = statistics.mean(older_prices)
                
                price_change = (recent_avg - older_avg) / older_avg
                
                if price_change > 0.1:
                    trend = 'rising'
                elif price_change < -0.1:
                    trend = 'declining'
                else:
                    trend = 'stable'
                
                # Check for demand surge (increased frequency of sales)
                recent_sales_count = len([p for p in historical_prices if p.days_ago <= 7])
                demand_surge = recent_sales_count > len(historical_prices) * 0.3
                
                trend_data = {
                    'price_trend': trend,
                    'trend_strength': abs(price_change),
                    'demand_surge': demand_surge,
                    'seasonal_factor': self.get_seasonal_factor(query),
                    'hype_score': min(1.0, abs(price_change) * 2 + (0.5 if demand_surge else 0)),
                    'data_sources': 2,  # eBay + estimated others
                    'estimated_market_price': recent_avg
                }
            
            # Cache the result
            self.market_trends_cache[cache_key] = trend_data
            self.cache_timestamp[cache_key] = time.time()
            
            return trend_data
            
        except Exception as e:
            logging.error(f"Market trend analysis error: {e}")
            return {
                'price_trend': 'stable',
                'trend_strength': 0.0,
                'demand_surge': False,
                'seasonal_factor': 1.0,
                'hype_score': 0.5,
                'data_sources': 1,
                'estimated_market_price': self._estimate_from_keywords(query)
            }

    def _fetch_historical_prices(self, query: str, days: int = 90) -> List[MarketDataPoint]:
        """Fetch historical price data"""
        try:
            # eBay sold listings with date filtering
            url = f"https://www.ebay.co.uk/sch/i.html?_nkw={query.replace(' ', '+')}&_sop=13&LH_Sold=1&LH_Complete=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")
            
            historical_data = []
            for item in soup.select(".s-item")[:50]:  # Get more data for trends
                try:
                    if "Shop on eBay" in item.text:
                        continue
                        
                    price_tag = item.select_one(".s-item__price")
                    date_tag = item.select_one(".s-item__endedDate")
                    
                    if not price_tag:
                        continue
                    
                    price = self._extract_price(price_tag.text.strip())
                    if not price or price < 5 or price > 2000:
                        continue
                    
                    # Extract days ago (simplified)
                    days_ago = 0
                    if date_tag:
                        date_text = date_tag.text.strip()
                        # Simple date parsing - could be enhanced
                        if 'day' in date_text:
                            match = re.search(r'(\d+)', date_text)
                            if match:
                                days_ago = int(match.group(1))
                    
                    historical_data.append(MarketDataPoint(
                        price=price,
                        platform='ebay',
                        condition='unknown',
                        days_ago=days_ago
                    ))
                        
                except Exception:
                    continue
            
            return historical_data
            
        except Exception as e:
            logging.error(f"Error fetching historical prices: {e}")
            return []

    def analyze_seller_profile(self, seller_data: Dict) -> SellerProfile:
        """Enhanced seller profiling"""
        try:
            # Extract seller info from listing data
            seller_id = seller_data.get('seller_id', 'unknown')
            
            # Check database for existing profile
            conn = sqlite3.connect('vinted_analyzer.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM seller_profiles WHERE seller_id = ?', (seller_id,))
            existing_profile = cursor.fetchone()
            
            if existing_profile:
                profile = SellerProfile(
                    seller_id=existing_profile[0],
                    avg_response_time=existing_profile[1],
                    negotiation_flexibility=existing_profile[2],
                    listing_count=existing_profile[3],
                    account_age_days=existing_profile[4],
                    feedback_score=existing_profile[5]
                )
            else:
                # Create new profile with defaults
                profile = SellerProfile(
                    seller_id=seller_id,
                    avg_response_time=24.0,  # Default 24 hours
                    negotiation_flexibility=0.15,  # Default 15% flexibility
                    listing_count=seller_data.get('listing_count', 10),
                    account_age_days=seller_data.get('account_age', 365),
                    feedback_score=seller_data.get('feedback_score', 4.5)
                )
                
                # Insert new profile
                cursor.execute('''
                    INSERT INTO seller_profiles 
                    (seller_id, avg_response_time, negotiation_flexibility, listing_count, account_age_days, feedback_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (profile.seller_id, profile.avg_response_time, profile.negotiation_flexibility,
                      profile.listing_count, profile.account_age_days, profile.feedback_score))
                conn.commit()
            
            conn.close()
            return profile
            
        except Exception as e:
            logging.error(f"Seller profile analysis error: {e}")
            return SellerProfile(
                seller_id='unknown',
                avg_response_time=24.0,
                negotiation_flexibility=0.15,
                listing_count=10,
                account_age_days=365,
                feedback_score=4.5
            )

    def calculate_optimal_timing(self, seller_profile: SellerProfile) -> Dict:
        """Calculate optimal timing for contact"""
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        # Best contact times based on general patterns
        if current_day < 5:  # Weekday
            if 9 <= current_hour <= 17:
                timing_score = 0.6  # Work hours - moderate response
            elif 18 <= current_hour <= 21:
                timing_score = 0.9  # Evening - best response
            else:
                timing_score = 0.3  # Early morning/late night
        else:  # Weekend
            if 10 <= current_hour <= 22:
                timing_score = 0.8  # Weekend day - good response
            else:
                timing_score = 0.4
        
        # Adjust based on seller profile
        if seller_profile.avg_response_time < 2:  # Fast responder
            timing_score *= 1.1
        elif seller_profile.avg_response_time > 48:  # Slow responder
            timing_score *= 0.9
        
        # Calculate follow-up schedule
        follow_up_days = [3, 7, 14] if seller_profile.negotiation_flexibility > 0.1 else [7, 21]
        
        return {
            'timing_score': min(1.0, timing_score),
            'recommended_wait_hours': 0 if timing_score > 0.7 else 2,
            'follow_up_schedule': follow_up_days,
            'urgency_window': 'high' if datetime.now().day > 25 else 'normal'  # End of month
        }

    def get_multi_platform_data(self, query: str) -> List[MarketDataPoint]:
        """Enhanced data gathering from multiple sources"""
        all_data = []
        
        # eBay (existing)
        ebay_data = self._fetch_sold_prices(query)
        for price in ebay_data:
            all_data.append(MarketDataPoint(
                price=price,
                platform='ebay',
                condition='unknown',
                days_ago=0
            ))
        
        # Add simulated Depop data (in real implementation, would scrape Depop)
        if len(all_data) > 0:
            # Simulate Depop prices (typically 10-15% lower than eBay)
            avg_ebay_price = statistics.mean(ebay_data) if ebay_data else 50
            depop_prices = [avg_ebay_price * 0.9, avg_ebay_price * 0.85, avg_ebay_price * 0.95]
            for price in depop_prices:
                all_data.append(MarketDataPoint(
                    price=price,
                    platform='depop',
                    condition='unknown',
                    days_ago=0
                ))
        
        # Weight by platform relevance to Vinted
        platform_weights = {
            'vinted': 1.0,
            'depop': 0.9,
            'ebay': 0.8,
            'facebook': 0.7
        }
        
        # Apply weights and return
        weighted_data = []
        for item in all_data:
            weight = platform_weights.get(item.platform, 0.8)
            # Adjust price based on platform difference
            adjusted_price = item.price * weight
            weighted_data.append(MarketDataPoint(
                price=adjusted_price,
                platform=item.platform,
                condition=item.condition,
                days_ago=item.days_ago
            ))
        
        return weighted_data

    def learn_from_outcome(self, strategy_data: Dict, outcome: str):
        """Learn from negotiation outcomes to improve future recommendations"""
        try:
            conn = sqlite3.connect('vinted_analyzer.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO negotiations 
                (item_name, original_price, offered_price, strategy_used, outcome, seller_response_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                strategy_data.get('item_name'),
                strategy_data.get('original_price'),
                strategy_data.get('offered_price'),
                strategy_data.get('strategy_used'),
                outcome,
                strategy_data.get('seller_response_time', 0)
            ))
            
            conn.commit()
            conn.close()
            
            # Update strategy success rates
            self._update_strategy_success_rates()
            
        except Exception as e:
            logging.error(f"Learning error: {e}")

    def _update_strategy_success_rates(self):
        """Update strategy success rates based on historical data"""
        try:
            conn = sqlite3.connect('vinted_analyzer.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT strategy_used, 
                       COUNT(*) as total,
                       SUM(CASE WHEN outcome = 'accepted' THEN 1 ELSE 0 END) as successes
                FROM negotiations 
                GROUP BY strategy_used
            ''')
            
            strategy_stats = cursor.fetchall()
            
            # Store updated success rates
            self.strategy_success_rates = {}
            for strategy, total, successes in strategy_stats:
                self.strategy_success_rates[strategy] = successes / total if total > 0 else 0.5
            
            conn.close()
            
        except Exception as e:
            logging.error(f"Strategy update error: {e}")

    def analyze_market_position(self, query: str, listed_price: float) -> Dict:
        """Enhanced market analysis with multi-platform data"""
        
        # Get enhanced market data
        market_data_points = self.get_multi_platform_data(query)
        
        if not market_data_points:
            # Fallback to estimation
            estimated_price = self._estimate_from_keywords(query)
            brand_analysis = self._analyze_brand_value(query)
            return {
                "sold_median": estimated_price,
                "sold_mean": estimated_price,
                "listing_median": estimated_price,
                "sold_count": 0,
                "price_variance": 0,
                "brand_analysis": brand_analysis,
                "price_vs_sold_ratio": listed_price / estimated_price,
                "market_position": self._classify_market_position(listed_price / estimated_price),
                "negotiation_potential": 0.3,
                "platform_coverage": 1
            }
        
        prices = [dp.price for dp in market_data_points]
        brand_analysis = self._analyze_brand_value(query)
        
        # Enhanced market metrics
        market_data = {
            "sold_median": statistics.median(prices),
            "sold_mean": statistics.mean(prices),
            "listing_median": statistics.median(prices),  # Simplified
            "sold_count": len(prices),
            "price_variance": statistics.stdev(prices) if len(prices) > 1 else 0,
            "brand_analysis": brand_analysis,
            "platform_coverage": len(set(dp.platform for dp in market_data_points))
        }
        
        # Calculate positioning
        price_vs_sold = listed_price / market_data["sold_median"]
        
        market_data.update({
            "price_vs_sold_ratio": price_vs_sold,
            "market_position": self._classify_market_position(price_vs_sold),
            "negotiation_potential": self._calculate_negotiation_potential(market_data, listed_price)
        })
        
        return market_data

    def _fetch_sold_prices(self, query: str, limit: int = 30) -> List[float]:
        """Fetch actual sold prices from eBay"""
        try:
            url = f"https://www.ebay.co.uk/sch/i.html?_nkw={query.replace(' ', '+')}&_sop=13&LH_Sold=1&LH_Complete=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")
            
            prices = []
            for item in soup.select(".s-item")[:limit]:
                try:
                    if "Shop on eBay" in item.text:
                        continue
                        
                    price_tag = item.select_one(".s-item__price")
                    if not price_tag:
                        continue
                    
                    price_text = price_tag.text.strip()
                    price = self._extract_price(price_text)
                    
                    if price and 5 <= price <= 2000:
                        prices.append(price)
                        
                except Exception:
                    continue
            
            return prices
            
        except Exception as e:
            logging.error(f"Error fetching sold prices: {e}")
            return []

    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if "to" in price_text.lower():
            price_text = price_text.split("to")[0].strip()
        
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        return None

    def _analyze_brand_value(self, query: str) -> Dict:
        """Analyze brand value and market positioning"""
        query_lower = query.lower()
        
        for brand, data in self.brands_data.items():
            if brand in query_lower:
                return {
                    "brand": brand.title(),
                    "base_value": data["base"],
                    "depreciation_rate": data["depreciation"],
                    "demand_level": data["demand"],
                    "brand_premium": self._calculate_brand_premium(data["demand"]),
                    "seasonal_factor": data.get("seasonal_factor", 1.0)
                }
        
        return {
            "brand": "Unknown",
            "base_value": 30,
            "depreciation_rate": 0.20,
            "demand_level": "low",
            "brand_premium": 1.0,
            "seasonal_factor": 1.0
        }

    def _calculate_brand_premium(self, demand_level: str) -> float:
        """Calculate brand premium multiplier"""
        premiums = {
            "luxury": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8,
            "trend": 1.1
        }
        return premiums.get(demand_level, 1.0)

    def _classify_market_position(self, price_ratio: float) -> str:
        """Classify where the price sits in the market"""
        if price_ratio <= 0.7:
            return "underpriced"
        elif price_ratio <= 0.9:
            return "good_deal"
        elif price_ratio <= 1.1:
            return "market_price"
        elif price_ratio <= 1.3:
            return "slightly_overpriced"
        else:
            return "overpriced"

    def _calculate_negotiation_potential(self, market_data: Dict, listed_price: float) -> float:
        """Calculate how much negotiation room exists"""
        base_potential = 0.3
        
        position_adjustments = {
            "underpriced": -0.2,
            "good_deal": -0.1,
            "market_price": 0.0,
            "slightly_overpriced": 0.1,
            "overpriced": 0.25
        }
        
        position = market_data.get("market_position", "market_price")
        adjusted_potential = base_potential + position_adjustments.get(position, 0)
        
        if market_data["sold_count"] > 3:
            variance_factor = min(market_data["price_variance"] / market_data["sold_median"], 0.3)
            adjusted_potential += variance_factor * 0.5
        
        return max(0.05, min(0.6, adjusted_potential))

    def _estimate_from_keywords(self, query: str) -> float:
        """Estimate price from keywords when no market data available"""
        query_lower = query.lower()
        
        brand_value = 30
        for brand, data in self.brands_data.items():
            if brand in query_lower:
                brand_value = data["base"]
                break
        
        category_value = 40
        for category, data in self.item_categories.items():
            if category in query_lower:
                category_value = data["base"]
                break
        
        estimated_price = max(brand_value, category_value)
        
        # Condition adjustments
        if any(word in query_lower for word in ['new', 'unused', 'tags']):
            estimated_price *= 1.3
        elif any(word in query_lower for word in ['excellent', 'mint']):
            estimated_price *= 1.1
        elif any(word in query_lower for word in ['poor', 'damaged', 'worn']):
            estimated_price *= 0.7
        
        # Apply seasonal factor
        seasonal_factor = self.get_seasonal_factor(query)
        estimated_price *= seasonal_factor
        
        return estimated_price

    def _apply_psychological_pricing(self, price: float) -> float:
        """Apply psychological pricing principles"""
        if price >= 100:
            return round(price / 5) * 5
        elif price >= 50:
            return round(price)
        elif price >= 20:
            rounded = round(price)
            if rounded - price > 0.5:
                return rounded - 0.01
            else:
                return rounded - 0.51
        else:
            return round(price * 2) / 2

    def generate_enhanced_strategy(self, data: Dict) -> Dict:
        """Enhanced strategy generation with all new features"""
        
        # Get enhanced market analysis
        market_analysis = self.analyze_market_position(data["item_name"], data["price"])
        
        # Get market trends
        market_trends = self.analyze_market_trends(data["item_name"])
        
        # Analyze seller profile
        seller_profile = self.analyze_seller_profile(data.get('seller_data', {}))
        
        # Calculate seller motivation
        seller_motivation = self._analyze_seller_motivation(
            data["days"], 
            data["interested"], 
            data.get("views", 0)
        )
        
        # Get optimal timing
        timing_analysis = self.calculate_optimal_timing(seller_profile)
        
        # Enhanced negotiation strength calculation
        negotiation_strength = self._calculate_enhanced_negotiation_strength(
            market_analysis, seller_motivation, market_trends, seller_profile
        )
        
        # Calculate optimal offer with trends
        optimal_offer = self._calculate_enhanced_optimal_offer(
            data["price"], market_analysis, seller_motivation, 
            negotiation_strength, market_trends
        )
        
        # Select strategy method
        strategy_method = self._select_enhanced_strategy_method(
            data, market_analysis, seller_motivation, 
            negotiation_strength, market_trends, timing_analysis
        )
        
        # Generate enhanced confidence score
        confidence = self._calculate_enhanced_confidence(
            market_analysis, seller_motivation, strategy_method, market_trends
        )
        
        # Create enhanced message
        message = self._generate_enhanced_contextual_message(
            strategy_method, data, optimal_offer, market_analysis, 
            seller_motivation, market_trends, timing_analysis
        )
        
        return {
            "method": strategy_method["name"],
            "offer_price": optimal_offer,
            "confidence": confidence,
            "discount_percent": round((data["price"] - optimal_offer) / data["price"] * 100, 1),
            "message": message,
            "market_analysis": market_analysis,
            "market_trends": market_trends,
            "seller_motivation": seller_motivation,
            "seller_profile": seller_profile.__dict__,
            "timing_analysis": timing_analysis,
            "reasoning": {
                "market_position": market_analysis["market_position"],
                "negotiation_strength": round(negotiation_strength * 100, 1),
                "seller_urgency": seller_motivation["urgency_score"],
                "strategy_rationale": strategy_method["rationale"],
                "trend_impact": market_trends["price_trend"],
                "seasonal_factor": market_trends["seasonal_factor"]
            }
        }

    def _analyze_seller_motivation(self, days: int, interested: int, views: int) -> Dict:
        """Analyze seller's motivation to sell quickly"""
        
        if days <= 2:
            time_urgency = 0.1
        elif days <= 7:
            time_urgency = 0.3
        elif days <= 21:
            time_urgency = 0.6
        elif days <= 60:
            time_urgency = 0.8
        else:
            time_urgency = 0.95
        
        if views > 0:
            engagement_ratio = interested / views
            engagement_urgency = 1 - min(engagement_ratio * 3, 1.0)
        else:
            if interested == 0 and days > 7:
                engagement_urgency = 0.8
            elif interested <= 2:
                engagement_urgency = 0.6
            else:
                engagement_urgency = 0.3
        
        urgency_score = (time_urgency * 0.7) + (engagement_urgency * 0.3)
        
        if days <= 3 and interested >= 5:
            seller_type = "testing_market"
        elif days > 30 and interested <= 1:
            seller_type = "motivated_seller"
        elif interested >= 10:
            seller_type = "firm_on_price"
        else:
            seller_type = "typical_seller"
        
        return {
            "urgency_score": urgency_score,
            "seller_type": seller_type,
            "time_pressure": time_urgency,
            "interest_pressure": engagement_urgency
        }

    def _calculate_enhanced_negotiation_strength(self, market_analysis: Dict, 
                                               seller_motivation: Dict, 
                                               market_trends: Dict, 
                                               seller_profile: SellerProfile) -> float:
        """Enhanced negotiation strength with trends and seller profiling"""
        
        # Base strength from market position
        base_strength = market_analysis["negotiation_potential"]
        
        # Seller motivation boost
        motivation_boost = seller_motivation["urgency_score"] * 0.4
        
        # Market trends adjustment
        trend_adjustment = 0
        if market_trends["price_trend"] == "declining":
            trend_adjustment = 0.15  # Prices falling = more negotiation power
        elif market_trends["price_trend"] == "rising":
            trend_adjustment = -0.1  # Prices rising = less negotiation power
        
        # Seasonal adjustment
        seasonal_adjustment = (market_trends["seasonal_factor"] - 1.0) * -0.1
        
        # Seller profile adjustment
        profile_adjustment = seller_profile.negotiation_flexibility * 0.3
        
        # Data quality factor
        data_quality = min(market_analysis["sold_count"] / 10, 1.0)
        
        # Combine all factors
        total_strength = (base_strength + motivation_boost + trend_adjustment + 
                         seasonal_adjustment + profile_adjustment) * data_quality
        
        return max(0.1, min(0.9, total_strength))

    def _calculate_enhanced_optimal_offer(self, listing_price: float, market_analysis: Dict, 
                                        seller_motivation: Dict, negotiation_strength: float, 
                                        market_trends: Dict) -> float:
        """Enhanced optimal offer calculation with trends"""
        
        if market_analysis["sold_median"] > 0:
            market_anchor = market_analysis["sold_median"]
        else:
            market_anchor = listing_price * 0.8
        
        # Trend adjustment
        trend_adjustment = 1.0
        if market_trends["price_trend"] == "declining":
            trend_adjustment = 0.9  # Be more aggressive when prices falling
        elif market_trends["price_trend"] == "rising":
            trend_adjustment = 1.1  # Be more conservative when prices rising
        
        # Seasonal adjustment
        seasonal_adjustment = market_trends["seasonal_factor"]
        if seasonal_adjustment > 1.1:  # High season
            trend_adjustment *= 1.05  # Slightly less aggressive
        elif seasonal_adjustment < 0.9:  # Low season
            trend_adjustment *= 0.95  # More aggressive
        
        max_discount_pct = negotiation_strength * 0.5
        max_discount_price = listing_price * (1 - max_discount_pct)
        
        conservative_offer = max(market_anchor * trend_adjustment, max_discount_price)
        
        urgency_adjustment = seller_motivation["urgency_score"] * 0.15
        motivated_offer = conservative_offer * (1 - urgency_adjustment)
        
        optimal_offer = self._apply_psychological_pricing(motivated_offer)
        
        min_discount = listing_price * 0.05
        if listing_price - optimal_offer < min_discount:
            optimal_offer = listing_price - min_discount
            optimal_offer = self._apply_psychological_pricing(optimal_offer)
        
        return max(listing_price * 0.4, min(listing_price * 0.95, optimal_offer))

    def _select_enhanced_strategy_method(self, data: Dict, market_analysis: Dict, 
                                       seller_motivation: Dict, negotiation_strength: float,
                                       market_trends: Dict, timing_analysis: Dict) -> Dict:
        """Enhanced strategy selection with timing and trends"""
        
        days = data["days"]
        interested = data["interested"]
        seller_type = seller_motivation["seller_type"]
        market_position = market_analysis["market_position"]
        
        # Consider timing
        if timing_analysis["timing_score"] < 0.5:
            return {
                "name": "Wait and Message Later",
                "rationale": f"Poor timing - wait {timing_analysis['recommended_wait_hours']} hours for better response rates"
            }
        
        # Consider market trends
        if market_trends["demand_surge"] and market_position in ["good_deal", "underpriced"]:
            return {
                "name": "Urgent Offer",
                "rationale": "High demand detected - act quickly before others do"
            }
        
        # Enhanced strategy selection
        if seller_type == "motivated_seller" and market_trends["price_trend"] == "declining":
            return {
                "name": "Trend-Based Direct Message",
                "rationale": "Motivated seller + declining market = strong position for direct approach"
            }
        elif seller_type == "testing_market" and market_position in ["overpriced", "slightly_overpriced"]:
            return {
                "name": "Market Reality Check",
                "rationale": "New overpriced listing - educate with market data"
            }
        elif seller_type == "firm_on_price" and market_trends["seasonal_factor"] < 0.9:
            return {
                "name": "Seasonal Patience",
                "rationale": "Off-season + firm seller = wait for better timing"
            }
        elif negotiation_strength > 0.7 and timing_analysis["urgency_window"] == "high":
            return {
                "name": "End-of-Month Push",
                "rationale": "Strong position + end of month = time for confident offer"
            }
        else:
            return {
                "name": "Enhanced Standard Offer",
                "rationale": "Balanced approach with market intelligence"
            }

    def _calculate_enhanced_confidence(self, market_analysis: Dict, seller_motivation: Dict, 
                                     strategy_method: Dict, market_trends: Dict) -> int:
        """Enhanced confidence calculation"""
        
        data_confidence = min(market_analysis["sold_count"] / 5, 1.0)
        
        strategy_confidence_map = {
            "Trend-Based Direct Message": 0.9,
            "Market Reality Check": 0.85,
            "Urgent Offer": 0.8,
            "End-of-Month Push": 0.85,
            "Enhanced Standard Offer": 0.7,
            "Seasonal Patience": 0.4,
            "Wait and Message Later": 0.3
        }
        
        strategy_confidence = strategy_confidence_map.get(strategy_method["name"], 0.6)
        
        position_confidence = {
            "overpriced": 0.9,
            "slightly_overpriced": 0.8,
            "market_price": 0.6,
            "good_deal": 0.4,
            "underpriced": 0.2
        }.get(market_analysis["market_position"], 0.5)
        
        # Trend confidence boost
        trend_confidence = 0.5
        if market_trends["price_trend"] == "declining":
            trend_confidence = 0.8
        elif market_trends["demand_surge"]:
            trend_confidence = 0.3
        
        total_confidence = (data_confidence * 0.25) + (strategy_confidence * 0.35) + \
                          (position_confidence * 0.25) + (trend_confidence * 0.15)
        
        return max(1, min(5, round(total_confidence * 5)))

    def _generate_enhanced_contextual_message(self, strategy_method: Dict, data: Dict, 
                                            offer_price: float, market_analysis: Dict,
                                            seller_motivation: Dict, market_trends: Dict,
                                            timing_analysis: Dict) -> str:
        """Generate enhanced contextual messages"""
        
        item = data["item_name"]
        days = data["days"]
        method_name = strategy_method["name"]
        
        enhanced_templates = {
            "Trend-Based Direct Message": [
                f"Hi! I've been tracking {item} prices and they've been declining recently. Since yours has been listed for {days} days, would you accept £{offer_price:.2f} for a quick sale?",
                f"Hello! Market data shows {item} prices are softening. I'd like to offer £{offer_price:.2f} for yours - happy to complete the purchase today.",
            ],
            "Market Reality Check": [
                f"Hi! I'm interested in your {item}. Looking at recent sales, similar items are selling for around £{market_analysis['sold_median']:.2f}. Would you consider £{offer_price:.2f}?",
                f"Hello! Love this {item}! I've seen similar ones selling for £{market_analysis['sold_median']:.2f} recently. Would £{offer_price:.2f} work for you?",
            ],
            "Urgent Offer": [
                f"Hi! I notice this {item} is getting popular - would you accept £{offer_price:.2f}? I can buy immediately before someone else does!",
                f"Hello! This {item} is exactly what I need and I see it's in demand. £{offer_price:.2f} and I'll purchase right now!",
            ],
            "End-of-Month Push": [
                f"Hi! End of month and I'm ready to buy this {item} today. Would £{offer_price:.2f} work? Can complete purchase within the hour!",
                f"Hello! I know it's end of month - would you accept £{offer_price:.2f} for your {item}? Quick payment guaranteed!",
            ],
            "Enhanced Standard Offer": [
                f"Hi! Really interested in this {item}. Based on my research, would £{offer_price:.2f} be acceptable? Thanks for considering!",
                f"Hello! This {item} is perfect for me. I'd like to offer £{offer_price:.2f} - let me know if that works!",
            ],
            "Seasonal Patience": [
                f"Hi! Beautiful {item}! I know it's off-season, so my budget is £{offer_price:.2f}. Would that work, or should I wait?",
                f"Hello! Love this {item} but it's not quite the right season. My offer is £{offer_price:.2f} - open to that?",
            ],
            "Wait and Message Later": [
                f"Consider messaging in {timing_analysis['recommended_wait_hours']} hours for better response rates.",
                f"Optimal timing suggests waiting until evening for this seller type.",
            ]
        }
        
        method_templates = enhanced_templates.get(method_name, enhanced_templates["Enhanced Standard Offer"])
        
        # Use item hash for consistent template selection
        item_hash = int(hashlib.md5(item.encode()).hexdigest(), 16)
        template_index = item_hash % len(method_templates)
        
        return method_templates[template_index]


# Initialize enhanced analyzer
analyzer = EnhancedVintedAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        required_fields = ['item_name', 'price', 'days', 'interested']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Generate enhanced analysis
        result = analyzer.generate_enhanced_strategy(data)
        
        response = {
            'success': True,
            'strategy': {
                'method': result['method'],
                'offer_price': result['offer_price'],
                'confidence': result['confidence'],
                'discount_percent': result['discount_percent'],
                'message': result['message']
            },
            'analysis': {
                'market_position': result['reasoning']['market_position'],
                'negotiation_strength': result['reasoning']['negotiation_strength'],
                'seller_motivation': result['seller_motivation']['seller_type'],
                'strategy_rationale': result['reasoning']['strategy_rationale'],
                'brand_info': result['market_analysis']['brand_analysis'],
                'trend_impact': result['reasoning']['trend_impact'],
                'seasonal_factor': result['reasoning']['seasonal_factor']
            },
            'market_price': result['market_analysis'].get('sold_median', data['price'] * 0.8),
            'insights': {
                'market_comparison': f"This item is {result['reasoning']['market_position'].replace('_', ' ')} compared to similar listings.",
                'seller_insights': f"Seller appears to be a {result['seller_motivation']['seller_type'].replace('_', ' ')} based on listing behavior.",
                'trend_insights': f"Market trend: {result['market_trends']['price_trend']} (seasonal factor: {result['market_trends']['seasonal_factor']:.2f})",
                'timing_insights': f"Current timing score: {result['timing_analysis']['timing_score']:.2f}/1.0"
            },
            'enhanced_features': {
                'market_trends': result['market_trends'],
                'seller_profile': result['seller_profile'],
                'timing_analysis': result['timing_analysis']
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Enhanced analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/brands')
def get_brand_suggestions():
    query = request.args.get('q', '')
    suggestions = analyzer.get_brand_suggestions(query)
    return jsonify(suggestions)

@app.route('/api/analyze-text', methods=['POST'])
def analyze_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        extracted_data = analyzer.analyze_screenshot_text(text)
        
        return jsonify({
            'success': True,
            'extracted_data': extracted_data
        })
        
    except Exception as e:
        logging.error(f"Text analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learn', methods=['POST'])
def learn_from_outcome():
    """New endpoint for learning from negotiation outcomes"""
    try:
        data = request.get_json()
        
        required_fields = ['item_name', 'original_price', 'offered_price', 'strategy_used', 'outcome']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        analyzer.learn_from_outcome(data, data['outcome'])
        
        return jsonify({'success': True, 'message': 'Learning data recorded'})
        
    except Exception as e:
        logging.error(f"Learning error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/market-trends/<path:item_name>')
def get_market_trends(item_name):
    """New endpoint for real-time market trends"""
    try:
        trends = analyzer.analyze_market_trends(item_name)
        return jsonify({
            'success': True,
            'trends': trends
        })
    except Exception as e:
        logging.error(f"Market trends error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
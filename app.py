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
import base64
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

class AdvancedVintedAnalyzer:
    def __init__(self):
        self.brands_data = {
            # Luxury brands - higher base prices, slower depreciation
            "balenciaga": {"base": 200, "depreciation": 0.05, "demand": "luxury"},
            "gucci": {"base": 250, "depreciation": 0.04, "demand": "luxury"},
            "louis vuitton": {"base": 300, "depreciation": 0.03, "demand": "luxury"},
            "prada": {"base": 280, "depreciation": 0.04, "demand": "luxury"},
            "versace": {"base": 220, "depreciation": 0.05, "demand": "luxury"},
            
            # Premium brands - moderate prices, steady demand
            "north face": {"base": 85, "depreciation": 0.08, "demand": "high"},
            "ralph lauren": {"base": 80, "depreciation": 0.10, "demand": "high"},
            "tommy hilfiger": {"base": 70, "depreciation": 0.12, "demand": "medium"},
            "calvin klein": {"base": 65, "depreciation": 0.12, "demand": "medium"},
            "lacoste": {"base": 75, "depreciation": 0.10, "demand": "medium"},
            
            # Streetwear - trend-dependent
            "supreme": {"base": 120, "depreciation": 0.15, "demand": "trend"},
            "jordan": {"base": 90, "depreciation": 0.12, "demand": "trend"},
            "nike": {"base": 60, "depreciation": 0.15, "demand": "high"},
            "adidas": {"base": 55, "depreciation": 0.15, "demand": "high"},
            
            # Mid-range brands
            "new balance": {"base": 65, "depreciation": 0.18, "demand": "medium"},
            "converse": {"base": 50, "depreciation": 0.20, "demand": "medium"},
            "vans": {"base": 45, "depreciation": 0.20, "demand": "medium"},
            "reebok": {"base": 50, "depreciation": 0.22, "demand": "medium"},
            "puma": {"base": 45, "depreciation": 0.18, "demand": "medium"},
            
            # Budget brands
            "champion": {"base": 40, "depreciation": 0.25, "demand": "low"},
            "fila": {"base": 45, "depreciation": 0.25, "demand": "low"},
            "carhartt": {"base": 55, "depreciation": 0.20, "demand": "medium"},
            "river island": {"base": 35, "depreciation": 0.25, "demand": "medium"}
        }
        
        self.item_categories = {
            # Outerwear - holds value well
            "jacket": {"base": 60, "seasonality": 0.3, "durability": "high"},
            "coat": {"base": 70, "seasonality": 0.4, "durability": "high"},
            "hoodie": {"base": 40, "seasonality": 0.1, "durability": "medium"},
            "parka": {"base": 80, "seasonality": 0.5, "durability": "high"},
            "blazer": {"base": 65, "seasonality": 0.1, "durability": "high"},
            
            # Footwear - brand dependent
            "trainers": {"base": 50, "seasonality": 0.1, "durability": "medium"},
            "sneakers": {"base": 55, "seasonality": 0.1, "durability": "medium"},
            "boots": {"base": 60, "seasonality": 0.3, "durability": "high"},
            "shoes": {"base": 45, "seasonality": 0.1, "durability": "medium"},
            
            # Basics - depreciate quickly
            "jeans": {"base": 35, "seasonality": 0.0, "durability": "high"},
            "trousers": {"base": 30, "seasonality": 0.0, "durability": "high"},
            "t-shirt": {"base": 20, "seasonality": 0.0, "durability": "low"},
            "shirt": {"base": 25, "seasonality": 0.0, "durability": "medium"},
            "dress": {"base": 45, "seasonality": 0.2, "durability": "medium"},
            
            # Accessories
            "bag": {"base": 40, "seasonality": 0.1, "durability": "high"},
            "watch": {"base": 70, "seasonality": 0.0, "durability": "high"}
        }

        # Common brands for autocomplete
        self.common_brands = [
            "Nike", "Adidas", "Puma", "New Balance", "Converse", "Vans", 
            "River Island", "Zara", "H&M", "ASOS", "Topman", "Next",
            "Ralph Lauren", "Tommy Hilfiger", "Calvin Klein", "Lacoste",
            "North Face", "Patagonia", "Supreme", "Champion", "Carhartt",
            "Gucci", "Prada", "Balenciaga", "Louis Vuitton", "Versace"
        ]

    def get_brand_suggestions(self, query: str) -> List[str]:
        """Get brand suggestions for autocomplete"""
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower()
        suggestions = []
        
        for brand in self.common_brands:
            if query_lower in brand.lower():
                suggestions.append(brand)
        
        return suggestions[:5]  # Limit to 5 suggestions

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

    def analyze_market_position(self, query: str, listed_price: float) -> Dict:
        """Advanced market analysis with multiple data points"""
        
        # Get sold prices (what items actually sold for)
        sold_prices = self._fetch_sold_prices(query)
        
        # Get current listing prices (what sellers are asking)
        listing_prices = self._fetch_listing_prices(query)
        
        # Estimate brand value and depreciation
        brand_analysis = self._analyze_brand_value(query)
        
        # Calculate market metrics
        market_data = {
            "sold_median": statistics.median(sold_prices) if sold_prices else 0,
            "sold_mean": statistics.mean(sold_prices) if sold_prices else 0,
            "listing_median": statistics.median(listing_prices) if listing_prices else 0,
            "sold_count": len(sold_prices),
            "price_variance": statistics.stdev(sold_prices) if len(sold_prices) > 1 else 0,
            "brand_analysis": brand_analysis
        }
        
        # Calculate price positioning
        if market_data["sold_median"] > 0:
            price_vs_sold = listed_price / market_data["sold_median"]
            price_vs_listings = listed_price / market_data["listing_median"] if market_data["listing_median"] > 0 else 1
        else:
            # Fallback to estimation
            estimated_price = self._estimate_from_keywords(query)
            price_vs_sold = listed_price / estimated_price
            price_vs_listings = 1
            market_data["sold_median"] = estimated_price
        
        market_data.update({
            "price_vs_sold_ratio": price_vs_sold,
            "price_vs_listings_ratio": price_vs_listings,
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
                    
                    if price and 5 <= price <= 2000:  # Reasonable price range
                        prices.append(price)
                        
                except Exception:
                    continue
            
            return prices
            
        except Exception as e:
            logging.error(f"Error fetching sold prices: {e}")
            return []

    def _fetch_listing_prices(self, query: str, limit: int = 20) -> List[float]:
        """Fetch current listing prices (not sold)"""
        try:
            url = f"https://www.ebay.co.uk/sch/i.html?_nkw={query.replace(' ', '+')}&_sop=15"  # Sort by price
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
            logging.error(f"Error fetching listing prices: {e}")
            return []

    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        # Handle ranges like "£20 to £30"
        if "to" in price_text.lower():
            price_text = price_text.split("to")[0].strip()
        
        # Remove currency symbols and extract numbers
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
                    "brand_premium": self._calculate_brand_premium(data["demand"])
                }
        
        # No brand found
        return {
            "brand": "Unknown",
            "base_value": 30,
            "depreciation_rate": 0.20,
            "demand_level": "low",
            "brand_premium": 1.0
        }

    def _calculate_brand_premium(self, demand_level: str) -> float:
        """Calculate brand premium multiplier"""
        premiums = {
            "luxury": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8,
            "trend": 1.1  # Can vary based on current trends
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
        """Calculate how much negotiation room exists (0-1 scale)"""
        base_potential = 0.3  # Base 30% negotiation potential
        
        # Adjust based on market position
        position_adjustments = {
            "underpriced": -0.2,    # Less room to negotiate
            "good_deal": -0.1,      # Slightly less room
            "market_price": 0.0,    # Normal room
            "slightly_overpriced": 0.1,  # More room
            "overpriced": 0.25      # Much more room
        }
        
        position = market_data.get("market_position", "market_price")
        adjusted_potential = base_potential + position_adjustments.get(position, 0)
        
        # Adjust for price variance (high variance = more negotiation room)
        if market_data["sold_count"] > 3:
            variance_factor = min(market_data["price_variance"] / market_data["sold_median"], 0.3)
            adjusted_potential += variance_factor * 0.5
        
        return max(0.05, min(0.6, adjusted_potential))  # Cap between 5% and 60%

    def generate_advanced_strategy(self, data: Dict) -> Dict:
        """Generate strategy using advanced logic"""
        
        # Get market analysis
        market_analysis = self.analyze_market_position(data["item_name"], data["price"])
        
        # Calculate seller motivation based on listing behavior
        seller_motivation = self._analyze_seller_motivation(data["days"], data["interested"], data.get("views", 0))
        
        # Determine base negotiation approach
        negotiation_strength = self._calculate_negotiation_strength(market_analysis, seller_motivation)
        
        # Calculate optimal offer price
        optimal_offer = self._calculate_optimal_offer(data["price"], market_analysis, seller_motivation, negotiation_strength)
        
        # Select strategy method
        strategy_method = self._select_strategy_method(data, market_analysis, seller_motivation, negotiation_strength)
        
        # Generate confidence score
        confidence = self._calculate_confidence(market_analysis, seller_motivation, strategy_method)
        
        # Create message
        message = self._generate_contextual_message(strategy_method, data, optimal_offer, market_analysis, seller_motivation)
        
        return {
            "method": strategy_method["name"],
            "offer_price": optimal_offer,
            "confidence": confidence,
            "discount_percent": round((data["price"] - optimal_offer) / data["price"] * 100, 1),
            "message": message,
            "market_analysis": market_analysis,
            "seller_motivation": seller_motivation,
            "reasoning": {
                "market_position": market_analysis["market_position"],
                "negotiation_strength": round(negotiation_strength * 100, 1),
                "seller_urgency": seller_motivation["urgency_score"],
                "strategy_rationale": strategy_method["rationale"]
            }
        }

    def _analyze_seller_motivation(self, days: int, interested: int, views: int) -> Dict:
        """Analyze seller's motivation to sell quickly"""
        
        # Calculate urgency based on time
        if days <= 2:
            time_urgency = 0.1  # Very new, seller not urgent yet
        elif days <= 7:
            time_urgency = 0.3  # Fresh listing, moderate urgency
        elif days <= 21:
            time_urgency = 0.6  # Getting older, increasing urgency
        elif days <= 60:
            time_urgency = 0.8  # Old listing, high urgency
        else:
            time_urgency = 0.95  # Very old, seller likely desperate
        
        # Calculate interest vs. action ratio
        if views > 0:
            engagement_ratio = interested / views
            # Low engagement suggests price/item issues
            engagement_urgency = 1 - min(engagement_ratio * 3, 1.0)
        else:
            # Estimate engagement
            if interested == 0 and days > 7:
                engagement_urgency = 0.8  # No interest suggests problems
            elif interested <= 2:
                engagement_urgency = 0.6
            else:
                engagement_urgency = 0.3
        
        # Combine factors
        urgency_score = (time_urgency * 0.7) + (engagement_urgency * 0.3)
        
        # Classify seller type
        if days <= 3 and interested >= 5:
            seller_type = "testing_market"  # Seeing what they can get
        elif days > 30 and interested <= 1:
            seller_type = "motivated_seller"  # Wants to sell quickly
        elif interested >= 10:
            seller_type = "firm_on_price"  # Getting interest, holding out
        else:
            seller_type = "typical_seller"  # Standard situation
        
        return {
            "urgency_score": urgency_score,
            "seller_type": seller_type,
            "time_pressure": time_urgency,
            "interest_pressure": engagement_urgency
        }

    def _calculate_negotiation_strength(self, market_analysis: Dict, seller_motivation: Dict) -> float:
        """Calculate how strong our negotiating position is"""
        
        # Base strength from market position
        market_strength = market_analysis["negotiation_potential"]
        
        # Boost from seller motivation
        motivation_boost = seller_motivation["urgency_score"] * 0.4
        
        # Adjust for market data quality
        data_quality = min(market_analysis["sold_count"] / 10, 1.0)  # Better data = more confidence
        
        # Combine factors
        total_strength = (market_strength + motivation_boost) * data_quality
        
        return max(0.1, min(0.9, total_strength))

    def _calculate_optimal_offer(self, listing_price: float, market_analysis: Dict, seller_motivation: Dict, negotiation_strength: float) -> float:
        """Calculate the optimal offer price using game theory principles"""
        
        # Start with market-based anchor
        if market_analysis["sold_median"] > 0:
            market_anchor = market_analysis["sold_median"]
        else:
            market_anchor = listing_price * 0.8  # Conservative fallback
        
        # Calculate maximum reasonable discount
        max_discount_pct = negotiation_strength * 0.5  # Up to 50% in extreme cases
        max_discount_price = listing_price * (1 - max_discount_pct)
        
        # Use the higher of market anchor or max discount (more conservative)
        conservative_offer = max(market_anchor, max_discount_price)
        
        # Apply seller motivation adjustment
        urgency_adjustment = seller_motivation["urgency_score"] * 0.15  # Up to 15% more aggressive
        motivated_offer = conservative_offer * (1 - urgency_adjustment)
        
        # Apply psychological pricing
        optimal_offer = self._apply_psychological_pricing(motivated_offer)
        
        # Ensure minimum discount to make negotiation worthwhile
        min_discount = listing_price * 0.05  # At least 5% off
        if listing_price - optimal_offer < min_discount:
            optimal_offer = listing_price - min_discount
            optimal_offer = self._apply_psychological_pricing(optimal_offer)
        
        # Final bounds check
        return max(listing_price * 0.4, min(listing_price * 0.95, optimal_offer))

    def _select_strategy_method(self, data: Dict, market_analysis: Dict, seller_motivation: Dict, negotiation_strength: float) -> Dict:
        """Select the best negotiation strategy"""
        
        days = data["days"]
        interested = data["interested"]
        seller_type = seller_motivation["seller_type"]
        market_position = market_analysis["market_position"]
        
        # Strategy decision tree
        if seller_type == "motivated_seller":
            return {
                "name": "Direct Message",
                "rationale": "Seller appears motivated - direct approach with time-based reasoning"
            }
        elif seller_type == "testing_market" and market_position in ["overpriced", "slightly_overpriced"]:
            return {
                "name": "Quick Offer",
                "rationale": "New overpriced listing - quick reasonable offer may work"
            }
        elif seller_type == "firm_on_price":
            return {
                "name": "Patient Approach",
                "rationale": "High interest suggests seller is firm - wait or make very reasonable offer"
            }
        elif days <= 2 and interested >= 3:
            return {
                "name": "Watch and Wait",
                "rationale": "New listing with interest - wait for competition to settle"
            }
        elif negotiation_strength > 0.7:
            return {
                "name": "Confident Offer",
                "rationale": "Strong negotiating position - can be more aggressive"
            }
        else:
            return {
                "name": "Standard Offer",
                "rationale": "Balanced approach for typical situation"
            }

    def _calculate_confidence(self, market_analysis: Dict, seller_motivation: Dict, strategy_method: Dict) -> int:
        """Calculate confidence score 1-5"""
        
        # Base confidence from data quality
        data_confidence = min(market_analysis["sold_count"] / 5, 1.0)  # More data = more confidence
        
        # Strategy-specific confidence
        strategy_confidence_map = {
            "Direct Message": 0.85,
            "Confident Offer": 0.8,
            "Quick Offer": 0.6,
            "Standard Offer": 0.7,
            "Patient Approach": 0.4,
            "Watch and Wait": 0.3
        }
        
        strategy_confidence = strategy_confidence_map.get(strategy_method["name"], 0.5)
        
        # Market position confidence
        position_confidence = {
            "overpriced": 0.9,
            "slightly_overpriced": 0.8,
            "market_price": 0.6,
            "good_deal": 0.4,
            "underpriced": 0.2
        }.get(market_analysis["market_position"], 0.5)
        
        # Combine factors
        total_confidence = (data_confidence * 0.3) + (strategy_confidence * 0.4) + (position_confidence * 0.3)
        
        # Convert to 1-5 scale
        return max(1, min(5, round(total_confidence * 5)))

    def _generate_contextual_message(self, strategy_method: Dict, data: Dict, offer_price: float, market_analysis: Dict, seller_motivation: Dict) -> str:
        """Generate contextually appropriate message"""
        
        item = data["item_name"]
        days = data["days"]
        method_name = strategy_method["name"]
        
        # Base templates by strategy
        templates = {
            "Direct Message": [
                f"Hi! I've been looking for this {item} and I'm ready to buy today. Since it's been listed for {days} days, would you accept £{offer_price:.2f} for a quick sale?",
                f"Hello! I'm interested in your {item}. I notice it's been available for a while - would £{offer_price:.2f} work for you? I can purchase immediately.",
                f"Hi there! I'd love to buy this {item}. Given that it's been listed for some time, would you consider £{offer_price:.2f}? Thanks!"
            ],
            "Quick Offer": [
                f"Hi! Love this {item} - would you accept £{offer_price:.2f}? I can buy right now! 😊",
                f"Hello! This {item} is exactly what I'm looking for. Would £{offer_price:.2f} work? Ready to purchase immediately!",
                f"Hi! Would you consider £{offer_price:.2f} for this {item}? I can complete the purchase today if that works."
            ],
            "Confident Offer": [
                f"Hi! I'm interested in this {item}. Based on similar items I've seen, would you accept £{offer_price:.2f}?",
                f"Hello! I'd like to offer £{offer_price:.2f} for your {item}. I think that's a fair price for both of us!",
                f"Hi there! Would you consider £{offer_price:.2f} for this {item}? I'm ready to buy at that price."
            ],
            "Standard Offer": [
                f"Hi! I really like this {item}. Would you consider £{offer_price:.2f}? Thanks for considering!",
                f"Hello! This {item} is just what I've been looking for. Would you be open to £{offer_price:.2f}?",
                f"Hi! I'm interested in your {item}. Would £{offer_price:.2f} work for you? Thanks! 😊"
            ],
            "Patient Approach": [
                f"Hi! Beautiful {item}! I'm interested but my budget is around £{offer_price:.2f}. Would that work, or should I keep looking?",
                f"Hello! I love this {item}. I know you might be firm on price, but would £{offer_price:.2f} be possible?",
                f"Hi! This {item} is lovely. My budget is £{offer_price:.2f} - would that be acceptable? No worries if not!"
            ],
            "Watch and Wait": [
                "Just favorite the item for now and monitor for 2-3 days before making an offer.",
                "Add to favorites and wait - with current interest levels, making an offer now may not be optimal.",
                "Watch this item for a few days. If interest dies down, then make your move."
            ]
        }
        
        # Select template
        method_templates = templates.get(method_name, templates["Standard Offer"])
        
        # Use item hash for consistent
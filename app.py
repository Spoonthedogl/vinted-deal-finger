from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
import os

# Import our improved analyzer
from vinted_analyzer import AdvancedVintedAnalyzer

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize analyzer
analyzer = AdvancedVintedAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        
        # Validate input
        required_fields = ['item_name', 'price', 'days', 'interested']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        # Validate data types and ranges
        try:
            data['price'] = float(data['price'])
            data['days'] = int(data['days'])
            data['interested'] = int(data['interested'])
            
            if data['price'] <= 0:
                return jsonify({"error": "Price must be greater than 0"}), 400
            if data['days'] < 0:
                return jsonify({"error": "Days cannot be negative"}), 400
            if data['interested'] < 0:
                return jsonify({"error": "Interested count cannot be negative"}), 400
                
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid data types"}), 400
        
        # Optional views field
        if 'views' in data:
            try:
                data['views'] = int(data['views'])
                if data['views'] < 0:
                    data['views'] = 0
            except (ValueError, TypeError):
                data['views'] = 0
        else:
            data['views'] = 0
        
        # Generate strategy using improved analyzer
        strategy = analyzer.generate_advanced_strategy(data)
        
        # Format response
        response = {
            "success": True,
            "market_price": strategy["market_analysis"]["sold_median"],
            "strategy": {
                "method": strategy["method"],
                "offer_price": strategy["offer_price"],
                "confidence": strategy["confidence"],
                "discount_percent": strategy["discount_percent"],
                "message": strategy["message"]
            },
            "analysis": {
                "market_position": strategy["market_analysis"]["market_position"],
                "seller_motivation": strategy["seller_motivation"]["seller_type"],
                "negotiation_strength": strategy["reasoning"]["negotiation_strength"],
                "brand_info": strategy["market_analysis"].get("brand_analysis", {})
            },
            "insights": {
                "market_comparison": _format_market_comparison(data["price"], strategy["market_analysis"]),
                "seller_insights": _format_seller_insights(strategy["seller_motivation"]),
                "strategy_rationale": strategy["reasoning"]["strategy_rationale"]
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Analysis error: {e}")
        return jsonify({"error": "Analysis failed. Please try again."}), 500

def _format_market_comparison(listing_price, market_analysis):
    """Format market comparison for frontend"""
    if market_analysis["sold_median"] > 0:
        ratio = listing_price / market_analysis["sold_median"]
        if ratio <= 0.8:
            return f"This item is priced {((1-ratio)*100):.0f}% below typical sold prices - great deal!"
        elif ratio <= 1.1:
            return "This item is priced around typical market value."
        elif ratio <= 1.3:
            return f"This item is priced {((ratio-1)*100):.0f}% above typical sold prices."
        else:
            return f"This item is priced {((ratio-1)*100):.0f}% above market - significant negotiation room!"
    else:
        return "Limited market data available for comparison."

def _format_seller_insights(seller_motivation):
    """Format seller insights for frontend"""
    urgency = seller_motivation["urgency_score"]
    seller_type = seller_motivation["seller_type"]
    
    insights = []
    
    if urgency > 0.7:
        insights.append("Seller appears motivated to sell quickly")
    elif urgency < 0.3:
        insights.append("Seller doesn't seem rushed to sell")
    
    type_descriptions = {
        "motivated_seller": "Seller likely wants to clear this item",
        "testing_market": "Seller is testing what price they can get",
        "firm_on_price": "Seller seems firm on their pricing",
        "typical_seller": "Standard selling situation"
    }
    
    insights.append(type_descriptions.get(seller_type, "Standard situation"))
    
    return ". ".join(insights) + "."

@app.route('/health')
def health_check():
    """Health check endpoint for deployment platforms"""
    return jsonify({"status": "healthy", "analyzer": "ready"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
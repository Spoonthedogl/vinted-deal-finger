class VintedProApp {
    constructor() {
        this.form = document.getElementById('analyzeForm');
        this.resultsSection = document.getElementById('results');
        this.errorMessage = document.getElementById('errorMessage');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.analyzeBtn = document.getElementById('analyzeBtn');
        this.btnText = document.querySelector('.btn-text');
        this.btnSpinner = document.querySelector('.btn-spinner');
        
        this.currentAnalysis = null;
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        document.getElementById('copyBtn').addEventListener('click', () => this.copyMessage());
        document.getElementById('editBtn').addEventListener('click', () => this.toggleEdit());
        
        // Auto-save form data
        this.loadFormData();
        this.form.addEventListener('input', () => this.saveFormData());
        
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js').catch(console.error);
        }
        
        // Show install prompt for iPhone users
        this.showInstallPrompt();
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const data = {
            item_name: formData.get('itemName').trim(),
            price: parseFloat(formData.get('price')),
            days: parseInt(formData.get('days')),
            interested: parseInt(formData.get('interested')),
            views: formData.get('views') ? parseInt(formData.get('views')) : undefined
        };

        if (!this.validateData(data)) {
            this.showError('Please fill in all required fields correctly.');
            return;
        }

        this.setLoading(true);
        this.hideResults();
        this.hideError();

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.currentAnalysis = result;
                this.displayResults(result, data);
                this.generateProTips(result, data);
            } else {
                throw new Error(result.error || 'Analysis failed');
            }

        } catch (error) {
            console.error('Analysis error:', error);
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }

    validateData(data) {
        return data.item_name && 
               data.item_name.length >= 3 &&
               data.price > 0 && 
               data.price <= 10000 &&
               data.days >= 0 && 
               data.days <= 365 &&
               data.interested >= 0 &&
               data.interested <= 1000;
    }

    setLoading(loading) {
        this.analyzeBtn.disabled = loading;
        this.loadingOverlay.style.display = loading ? 'flex' : 'none';
        
        if (loading) {
            this.btnText.style.display = 'none';
            this.btnSpinner.style.display = 'inline-block';
        } else {
            this.btnText.style.display = 'inline-block';
            this.btnSpinner.style.display = 'none';
        }
    }

    displayResults(result, originalData) {
        const { market_price, strategy, analysis, insights } = result;
        
        // Market analysis
        this.updateMarketAnalysis(market_price, strategy, originalData, insights);
        
        // Strategy details
        this.updateStrategy(strategy, analysis);
        
        // Seller insights
        this.updateSellerInsights(analysis, insights);
        
        // Brand analysis (if available)
        this.updateBrandAnalysis(analysis.brand_info);
        
        // Message template
        this.updateMessageTemplate(strategy.message);
        
        // Show results with animation
        this.showResults();
    }

    updateMarketAnalysis(marketPrice, strategy, originalData, insights) {
        document.getElementById('marketPrice').textContent = marketPrice.toFixed(2);
        
        const savings = originalData.price - strategy.offer_price;
        const savingsElement = document.getElementById('savings');
        
        if (savings > 0) {
            savingsElement.textContent = `£${savings.toFixed(2)} (${strategy.discount_percent}%)`;
            savingsElement.className = 'value savings positive';
        } else {
            savingsElement.textContent = 'Item is well-priced';
            savingsElement.className = 'value savings neutral';
        }
        
        document.getElementById('marketComparison').textContent = insights.market_comparison;
    }

    updateStrategy(strategy, analysis) {
        const methodIcons = {
            'Quick Offer': '⚡',
            'Standard Offer': '💬',
            'Direct Message': '📝',
            'Confident Offer': '🎯',
            'Patient Approach': '🕐',
            'Watch and Wait': '👀'
        };
        
        document.getElementById('strategyIcon').textContent = methodIcons[strategy.method] || '💬';
        document.getElementById('strategyMethod').textContent = strategy.method;
        document.getElementById('offerPrice').textContent = strategy.offer_price.toFixed(2);
        document.getElementById('discountPercent').textContent = strategy.discount_percent;
        
        // Confidence stars
        const confidence = Math.max(1, Math.min(5, strategy.confidence));
        const stars = '★'.repeat(confidence) + '☆'.repeat(5 - confidence);
        document.getElementById('confidence').textContent = stars;
        
        // Negotiation strength
        const strengthElement = document.getElementById('negotiationStrength');
        strengthElement.textContent = analysis.negotiation_strength;
        strengthElement.className = this.getStrengthClass(analysis.negotiation_strength);
        
        // Strategy rationale
        document.getElementById('strategyRationale').textContent = analysis.strategy_rationale;
    }

    updateSellerInsights(analysis, insights) {
        document.getElementById('sellerInsights').textContent = insights.seller_insights;
        
        const sellerTypeElement = document.getElementById('sellerType');
        sellerTypeElement.textContent = this.formatSellerType(analysis.seller_motivation);
        sellerTypeElement.className = `type-badge ${analysis.seller_motivation.replace('_', '-')}`;
    }

    updateBrandAnalysis(brandInfo) {
        const brandCard = document.getElementById('brandAnalysis');
        
        if (brandInfo && brandInfo.brand !== 'Unknown') {
            brandCard.style.display = 'block';
            document.getElementById('brandName').textContent = brandInfo.brand;
            document.getElementById('brandTier').textContent = this.formatBrandTier(brandInfo.demand_level);
            document.getElementById('brandValue').textContent = `£${brandInfo.base_value}`;
        } else {
            brandCard.style.display = 'none';
        }
    }

    updateMessageTemplate(message) {
        const templateElement = document.getElementById('messageTemplate');
        const editableElement = document.getElementById('editableMessage');
        
        templateElement.textContent = message;
        editableElement.value = message;
    }

    generateProTips(result, originalData) {
        const tipsContainer = document.getElementById('proTips');
        const tips = [];
        
        // Market-based tips
        if (result.analysis.market_position === 'overpriced') {
            tips.push("💡 This item is overpriced - you have strong negotiating power!");
        } else if (result.analysis.market_position === 'underpriced') {
            tips.push("⚠️ This is already a good deal - don't push too hard on price.");
        }
        
        // Time-based tips
        if (originalData.days > 30) {
            tips.push("⏰ Old listings often mean motivated sellers - mention the listing age.");
        } else if (originalData.days <= 2) {
            tips.push("🆕 For new listings, consider waiting a few days if not urgent.");
        }
        
        // Interest-based tips
        if (originalData.interested === 0) {
            tips.push("🎯 No other interest gives you negotiating power - be confident!");
        } else if (originalData.interested > 10) {
            tips.push("🏃‍♂️ High interest means act quickly with a reasonable offer.");
        }
        
        // Strategy-specific tips
        if (result.strategy.method === 'Watch and Wait') {
            tips.push("👀 Patience pays off - favorite the item and monitor for changes.");
        } else if (result.strategy.method === 'Direct Message') {
            tips.push("💬 Personal messages work better than automated offers for this situation.");
        }
        
        // General tips
        tips.push("🤝 Always be polite and respectful - it goes a long way!");
        tips.push("📱 Respond quickly if the seller counters your offer.");
        
        // Render tips
        tipsContainer.innerHTML = tips.map(tip => `<div class="tip-item">${tip}</div>`).join('');
    }

    getStrengthClass(strength) {
        if (strength >= 70) return 'strength-value high';
        if (strength >= 40) return 'strength-value medium';
        return 'strength-value low';
    }

    formatSellerType(sellerType) {
        const typeMap = {
            'motivated_seller': 'Motivated Seller',
            'testing_market': 'Testing Market',
            'firm_on_price': 'Firm on Price',
            'typical_seller': 'Typical Seller'
        };
        return typeMap[sellerType] || 'Unknown';
    }

    formatBrandTier(demandLevel) {
        const tierMap = {
            'luxury': 'Luxury Brand',
            'high': 'Premium Brand',
            'medium': 'Mid-Range Brand',
            'low': 'Budget Brand',
            'trend': 'Streetwear/Trend'
        };
        return tierMap[demandLevel] || 'Standard Brand';
    }

    async copyMessage() {
        const messageText = document.getElementById('editableMessage').style.display === 'none' 
            ? document.getElementById('messageTemplate').textContent
            : document.getElementById('editableMessage').value;
            
        const copyBtn = document.getElementById('copyBtn');
        
        try {
            await navigator.clipboard.writeText(messageText);
            
            // Success feedback
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✅ Copied!';
            copyBtn.classList.add('copied');
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.remove('copied');
            }, 2000);
            
        } catch (err) {
            console.error('Copy failed:', err);
            this.fallbackCopy(messageText, copyBtn);
        }
    }

    fallbackCopy(text, button) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            button.textContent = '✅ Copied!';
        } catch (err) {
            button.textContent = '❌ Copy failed';
        }
        
        document.body.removeChild(textArea);
        
        setTimeout(() => {
            button.textContent = '📋 Copy Message';
        }, 2000);
    }

    toggleEdit() {
        const messageTemplate = document.getElementById('messageTemplate');
        const editableMessage = document.getElementById('editableMessage');
        const editBtn = document.getElementById('editBtn');
        
        if (editableMessage.style.display === 'none') {
            // Switch to edit mode
            messageTemplate.style.display = 'none';
            editableMessage.style.display = 'block';
            editableMessage.focus();
            editBtn.textContent = '💾 Save';
        } else {
            // Switch to view mode
            messageTemplate.textContent = editableMessage.value;
            messageTemplate.style.display = 'block';
            editableMessage.style.display = 'none';
            editBtn.textContent = '✏️ Edit';
        }
    }

    showResults() {
        this.resultsSection.style.display = 'block';
        this.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Animate cards
        const cards = this.resultsSection.querySelectorAll('.result-card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.display = 'block';
                
                setTimeout(() => {
                    card.style.transition = 'all 0.5s ease-out';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 50);
            }, index * 100);
        });
    }

    hideResults() {
        this.resultsSection.style.display = 'none';
    }

    showError(message) {
        const errorElement = this.errorMessage.querySelector('p');
        errorElement.textContent = `❌ ${message}`;
        this.errorMessage.style.display = 'block';
        this.errorMessage.scrollIntoView({ behavior: 'smooth' });
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }

    hideError() {
        this.errorMessage.style.display = 'none';
    }

    // Form data persistence
    saveFormData() {
        const formData = new FormData(this.form);
        const data = {
            item_name: formData.get('itemName'),
            price: formData.get('price'),
            days: formData.get('days'),
            interested: formData.get('interested'),
            views: formData.get('views')
        };
        
        try {
            localStorage.setItem('vintedFormData', JSON.stringify(data));
        } catch (e) {
            // Ignore if localStorage not available
        }
    }

    loadFormData() {
        try {
            const saved = localStorage.getItem('vintedFormData');
            if (saved) {
                const data = JSON.parse(saved);
                
                if (data.item_name) document.getElementById('itemName').value = data.item_name;
                if (data.price) document.getElementById('price').value = data.price;
                if (data.days) document.getElementById('days').value = data.days;
                if (data.interested) document.getElementById('interested').value = data.interested;
                if (data.views) document.getElementById('views').value = data.views;
            }
        } catch (e) {
            // Ignore if data is corrupted
        }
    }

    showInstallPrompt() {
        // Check if iOS and not in standalone mode
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        const isStandalone = window.navigator.standalone === true || 
                           window.matchMedia('(display-mode: standalone)').matches;
        
        if (isIOS && !isStandalone) {
            setTimeout(() => {
                const banner = document.createElement('div');
                banner.className = 'install-banner';
                banner.innerHTML = `
                    <div class="install-content">
                        <span class="install-icon">📱</span>
                        <div class="install-text">
                            <strong>Add to Home Screen</strong>
                            <small>For the best app experience</small>
                        </div>
                        <button class="install-close">×</button>
                    </div>
                `;
                
                banner.querySelector('.install-close').onclick = () => {
                    banner.remove();
                    localStorage.setItem('installPromptDismissed', 'true');
                };
                
                // Don't show if previously dismissed
                if (!localStorage.getItem('installPromptDismissed')) {
                    document.body.appendChild(banner);
                    
                    // Auto-hide after 10 seconds
                    setTimeout(() => {
                        if (banner.parentNode) {
                            banner.remove();
                        }
                    }, 10000);
                }
            }, 3000);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new VintedProApp();
});

// Handle online/offline status
window.addEventListener('online', () => {
    const statusBanner = document.createElement('div');
    statusBanner.textContent = '✅ Back online';
    statusBanner.className = 'status-banner online';
    document.body.appendChild(statusBanner);
    
    setTimeout(() => statusBanner.remove(), 3000);
});

window.addEventListener('offline', () => {
    const statusBanner = document.createElement('div');
    statusBanner.textContent = '⚠️ You\'re offline - some features may not work';
    statusBanner.className = 'status-banner offline';
    document.body.appendChild(statusBanner);
    
    setTimeout(() => statusBanner.remove(), 5000);
});
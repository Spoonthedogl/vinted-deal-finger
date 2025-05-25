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
        this.recentItems = this.loadRecentItems();
        
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        document.getElementById('copyBtn').addEventListener('click', () => this.copyMessage());
        document.getElementById('editBtn').addEventListener('click', () => this.toggleEdit());
        document.getElementById('retryBtn').addEventListener('click', () => this.retryAnalysis());
        
        // Dark mode toggle
        document.getElementById('darkModeToggle').addEventListener('click', () => this.toggleDarkMode());
        
        // Smart fill functionality
        document.getElementById('smartFillBtn').addEventListener('click', () => this.toggleSmartFill());
        document.getElementById('extractBtn').addEventListener('click', () => this.extractFromText());
        
        // Quick selectors
        this.setupQuickSelectors();
        
        // Condition toggles
        this.setupConditionToggles();
        
        // Brand autocomplete
        this.setupBrandAutocomplete();
        
        // Load saved theme
        this.loadTheme();
        
        // Auto-save form data
        this.loadFormData();
        this.form.addEventListener('input', () => this.saveFormData());
        
        // Display recent items
        this.displayRecentItems();
        
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js').catch(console.error);
        }
        
        // Show install prompt for iPhone users
        this.showInstallPrompt();
        
        // Setup haptic feedback
        this.setupHapticFeedback();
    }

    setupQuickSelectors() {
        const quickSelectors = document.querySelectorAll('.quick-selector');
        quickSelectors.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const value = btn.dataset.value;
                const input = btn.closest('.form-group').querySelector('input');
                input.value = value;
                
                // Update visual state
                btn.parentElement.querySelectorAll('.quick-selector').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                this.triggerHaptic();
            });
        });
    }

    setupConditionToggles() {
        const conditionToggles = document.querySelectorAll('.condition-toggle');
        conditionToggles.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const condition = btn.dataset.condition;
                const itemNameInput = document.getElementById('itemName');
                
                // Toggle active state
                conditionToggles.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Add condition to item name if not already there
                let itemName = itemNameInput.value.trim();
                const conditionWords = ['new', 'excellent', 'good', 'used', 'worn'];
                
                // Remove existing condition words
                conditionWords.forEach(word => {
                    const regex = new RegExp(`\\b${word}\\b`, 'gi');
                    itemName = itemName.replace(regex, '').trim();
                });
                
                // Add new condition
                itemNameInput.value = `${itemName} ${condition}`.trim();
                
                this.triggerHaptic();
            });
        });
    }

    setupBrandAutocomplete() {
        const itemNameInput = document.getElementById('itemName');
        const suggestionsDiv = document.getElementById('itemSuggestions');
        let debounceTimer;

        itemNameInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                suggestionsDiv.style.display = 'none';
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/brands?q=${encodeURIComponent(query)}`);
                    const suggestions = await response.json();
                    
                    if (suggestions.length > 0) {
                        this.displaySuggestions(suggestions, suggestionsDiv, itemNameInput);
                    } else {
                        suggestionsDiv.style.display = 'none';
                    }
                } catch (error) {
                    console.error('Error fetching suggestions:', error);
                }
            }, 300);
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!itemNameInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
                suggestionsDiv.style.display = 'none';
            }
        });
    }

    displaySuggestions(suggestions, container, input) {
        container.innerHTML = '';
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = suggestion;
            item.addEventListener('click', () => {
                const currentValue = input.value.trim();
                const words = currentValue.split(' ');
                
                // Replace the first word with the selected brand
                words[0] = suggestion;
                input.value = words.join(' ');
                container.style.display = 'none';
                
                this.triggerHaptic();
            });
            container.appendChild(item);
        });
        container.style.display = 'block';
    }

    toggleDarkMode() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        this.triggerHaptic();
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    toggleSmartFill() {
        const smartFillArea = document.getElementById('smartFillArea');
        const isVisible = smartFillArea.style.display !== 'none';
        
        smartFillArea.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            document.getElementById('textInput').focus();
        }
        
        this.triggerHaptic();
    }

    async extractFromText() {
        const textInput = document.getElementById('textInput');
        const text = textInput.value.trim();
        
        if (!text) {
            this.showToast('Please enter some text to analyze', 'error');
            return;
        }

        try {
            const response = await fetch('/api/analyze-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const result = await response.json();
            
            if (result.success) {
                this.fillFormFromExtractedData(result.extracted_data);
                this.showToast('Information extracted successfully!', 'success');
                this.toggleSmartFill(); // Hide the smart fill area
            } else {
                this.showToast('Could not extract information from text', 'error');
            }
        } catch (error) {
            console.error('Error extracting text:', error);
            this.showToast('Failed to analyze text', 'error');
        }
    }

    fillFormFromExtractedData(data) {
        if (data.item_name) {
            document.getElementById('itemName').value = data.item_name;
        }
        if (data.brand) {
            const currentName = document.getElementById('itemName').value;
            if (!currentName.toLowerCase().includes(data.brand.toLowerCase())) {
                document.getElementById('itemName').value = `${data.brand} ${currentName}`.trim();
            }
        }
        if (data.upload_time !== undefined) {
            document.getElementById('days').value = data.upload_time;
        }
        if (data.views !== undefined) {
            document.getElementById('views').value = data.views;
        }
        
        // Auto-fill some reasonable defaults based on extracted data
        if (data.upload_time === 0) {
            document.getElementById('interested').value = data.views > 5 ? Math.floor(data.views * 0.2) : 0;
        }
        
        this.triggerHaptic();
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
                this.currentAnalysis = { result, originalData: data };
                this.addToRecentItems(data);
                this.displayResults(result, data);
                this.generateProTips(result, data);
                this.triggerHaptic();
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
            this.updateLoadingStatus();
        } else {
            this.btnText.style.display = 'inline-block';
            this.btnSpinner.style.display = 'none';
        }
    }

    updateLoadingStatus() {
        const statusMessages = [
            'Fetching eBay data...',
            'Analyzing market trends...',
            'Calculating negotiation strategy...',
            'Generating recommendations...'
        ];
        
        let currentIndex = 0;
        const statusElement = document.getElementById('loadingStatus');
        
        const updateStatus = () => {
            if (statusElement && this.loadingOverlay.style.display === 'flex') {
                statusElement.textContent = statusMessages[currentIndex];
                currentIndex = (currentIndex + 1) % statusMessages.length;
                setTimeout(updateStatus, 1500);
            }
        };
        
        updateStatus();
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
            
            // Success feedback with haptic
            this.triggerHaptic();
            this.showToast('Message copied to clipboard!', 'success');
            
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
            this.showToast('Message copied!', 'success');
        } catch (err) {
            button.textContent = '❌ Copy failed';
            this.showToast('Copy failed', 'error');
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
        
        this.triggerHaptic();
    }

    retryAnalysis() {
        if (this.currentAnalysis) {
            // Modify the current data slightly for retry
            const data = { ...this.currentAnalysis.originalData };
            
            // Create a new FormData and populate the form
            document.getElementById('itemName').value = data.item_name;
            document.getElementById('price').value = data.price;
            document.getElementById('days').value = data.days;
            document.getElementById('interested').value = data.interested;
            if (data.views) document.getElementById('views').value = data.views;
            
            // Scroll to form
            this.form.scrollIntoView({ behavior: 'smooth' });
            this.triggerHaptic();
        }
    }

    showResults() {
        this.resultsSection.style.display = 'block';
        this.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Animate cards with stagger effect
        const cards = this.resultsSection.querySelectorAll('.result-card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('visible');
            }, index * 150);
        });
    }

    hideResults() {
        this.resultsSection.style.display = 'none';
        const cards = this.resultsSection.querySelectorAll('.result-card');
        cards.forEach(card => card.classList.remove('visible'));
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

    showToast(message, type = 'success') {
        const toast = document.getElementById('successToast');
        const messageElement = toast.querySelector('.toast-message');
        const iconElement = toast.querySelector('.toast-icon');
        
        messageElement.textContent = message;
        
        if (type === 'error') {
            iconElement.textContent = '❌';
            toast.style.background = 'var(--error-color)';
        } else {
            iconElement.textContent = '✅';
            toast.style.background = 'var(--success-color)';
        }
        
        toast.style.display = 'flex';
        
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }

    // Recent Items Management
    loadRecentItems() {
        try {
            const saved = localStorage.getItem('vintedRecentItems');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            return [];
        }
    }

    saveRecentItems() {
        try {
            localStorage.setItem('vintedRecentItems', JSON.stringify(this.recentItems));
        } catch (e) {
            // Ignore if localStorage not available
        }
    }

    addToRecentItems(data) {
        const item = {
            item_name: data.item_name,
            price: data.price,
            days: data.days,
            interested: data.interested,
            views: data.views,
            timestamp: Date.now()
        };
        
        // Remove duplicates
        this.recentItems = this.recentItems.filter(i => i.item_name !== data.item_name);
        
        // Add to beginning
        this.recentItems.unshift(item);
        
        // Keep only last 5 items
        this.recentItems = this.recentItems.slice(0, 5);
        
        this.saveRecentItems();
        this.displayRecentItems();
    }

    displayRecentItems() {
        const container = document.getElementById('recentItemsList');
        const recentSection = document.getElementById('recentItems');
        
        if (this.recentItems.length === 0) {
            recentSection.style.display = 'none';
            return;
        }
        
        recentSection.style.display = 'block';
        
        container.innerHTML = this.recentItems.map((item, index) => `
            <div class="recent-item" data-index="${index}">
                ${item.item_name.substring(0, 30)}${item.item_name.length > 30 ? '...' : ''}
                <button class="delete-btn" data-index="${index}">×</button>
            </div>
        `).join('');
        
        // Add event listeners
        container.querySelectorAll('.recent-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('delete-btn')) {
                    e.stopPropagation();
                    this.deleteRecentItem(parseInt(e.target.dataset.index));
                } else {
                    this.loadRecentItem(parseInt(item.dataset.index));
                }
            });
        });
    }

    loadRecentItem(index) {
        const item = this.recentItems[index];
        if (!item) return;
        
        document.getElementById('itemName').value = item.item_name;
        document.getElementById('price').value = item.price;
        document.getElementById('days').value = item.days;
        document.getElementById('interested').value = item.interested;
        if (item.views) document.getElementById('views').value = item.views;
        
        this.triggerHaptic();
        this.form.scrollIntoView({ behavior: 'smooth' });
    }

    deleteRecentItem(index) {
        this.recentItems.splice(index, 1);
        this.saveRecentItems();
        this.displayRecentItems();
        this.triggerHaptic();
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

    // Haptic Feedback
    setupHapticFeedback() {
        // Add haptic feedback to buttons
        const buttons = document.querySelectorAll('button, .recent-item, .suggestion-item');
        buttons.forEach(button => {
            button.addEventListener('click', () => this.triggerHaptic());
        });
    }

    triggerHaptic() {
        // Trigger device haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(50); // 50ms vibration
        }
        
        // Visual feedback for non-haptic devices
        document.body.classList.add('haptic-feedback');
        setTimeout(() => {
            document.body.classList.remove('haptic-feedback');
        }, 100);
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

// Add this enhanced market scan functionality to your app.js

async performMarketScan() {
    const itemName = document.getElementById('itemName').value.trim();
    
    if (!itemName || itemName.length < 3) {
        this.showToast('Enter an item name first (at least 3 characters)', 'error');
        return;
    }
    
    // Show loading state
    const scanBtn = document.getElementById('marketScanBtn');
    const originalText = scanBtn.textContent;
    scanBtn.textContent = '🔄 Scanning...';
    scanBtn.disabled = true;
    
    try {
        // Get real-time market trends
        const response = await fetch(`/api/market-trends/${encodeURIComponent(itemName)}`);
        const data = await response.json();
        
        if (data.success) {
            this.displayMarketScanResults(data.trends, itemName);
        } else {
            this.showToast('Market scan failed - try again', 'error');
        }
    } catch (error) {
        console.error('Market scan error:', error);
        this.showToast('Market scan failed - check your connection', 'error');
    } finally {
        // Reset button
        scanBtn.textContent = originalText;
        scanBtn.disabled = false;
    }
}

displayMarketScanResults(trends, itemName) {
    // Create or update market scan results panel
    let scanResults = document.getElementById('marketScanResults');
    
    if (!scanResults) {
        scanResults = document.createElement('div');
        scanResults.id = 'marketScanResults';
        scanResults.className = 'market-scan-results';
        
        // Insert after quick tools
        const quickTools = document.querySelector('.quick-tools');
        quickTools.parentNode.insertBefore(scanResults, quickTools.nextSibling);
    }
    
    // Calculate market insights
    const priceDirection = trends.price_trend === 'rising' ? '📈 Rising' : 
                          trends.price_trend === 'declining' ? '📉 Declining' : '📊 Stable';
    
    const demandLevel = trends.demand_surge ? '🔥 High Demand' : 
                       trends.hype_score > 0.6 ? '📊 Moderate Demand' : '💤 Low Demand';
    
    const seasonalImpact = trends.seasonal_factor > 1.1 ? '❄️ Peak Season (+25%)' :
                          trends.seasonal_factor < 0.9 ? '🌞 Off Season (-20%)' : '📅 Normal Season';
    
    const marketAdvice = this.generateMarketAdvice(trends);
    
    scanResults.innerHTML = `
        <div class="scan-results-header">
            <h3>🔍 Market Scan Results for "${itemName}"</h3>
            <button class="close-scan-btn" onclick="this.parentElement.parentElement.style.display='none'">×</button>
        </div>
        
        <div class="scan-metrics">
            <div class="scan-metric">
                <span class="scan-label">Price Trend (30 days)</span>
                <span class="scan-value trend-${trends.price_trend}">${priceDirection}</span>
            </div>
            <div class="scan-metric">
                <span class="scan-label">Market Demand</span>
                <span class="scan-value">${demandLevel}</span>
            </div>
            <div class="scan-metric">
                <span class="scan-label">Seasonal Impact</span>
                <span class="scan-value">${seasonalImpact}</span>
            </div>
            <div class="scan-metric">
                <span class="scan-label">Estimated Market Price</span>
                <span class="scan-value market-price">£${trends.estimated_market_price?.toFixed(2) || 'N/A'}</span>
            </div>
        </div>
        
        <div class="market-advice">
            <h4>💡 Market Intelligence</h4>
            <ul class="advice-list">
                ${marketAdvice.map(advice => `<li>${advice}</li>`).join('')}
            </ul>
        </div>
        
        <div class="scan-actions">
            <button class="auto-fill-btn" onclick="vintedApp.autoFillFromScan(${trends.estimated_market_price || 50})">
                📝 Auto-fill Price
            </button>
            <button class="watch-market-btn" onclick="vintedApp.watchMarket('${itemName}')">
                👀 Watch This Market
            </button>
        </div>
    `;
    
    scanResults.style.display = 'block';
    
    // Smooth scroll to results
    scanResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Show success message
    this.showToast(`✅ Market scan complete for ${itemName}`, 'success');
    
    // Auto-update price indicator if price field is filled
    const priceInput = document.getElementById('price');
    if (priceInput.value && trends.estimated_market_price) {
        this.updatePriceIndicatorFromScan(parseFloat(priceInput.value), trends.estimated_market_price);
    }
}

generateMarketAdvice(trends) {
    const advice = [];
    
    // Price trend advice
    if (trends.price_trend === 'declining') {
        advice.push('🎯 <strong>Buyer\'s market</strong> - Prices are falling, you have negotiation power');
        advice.push('⏰ Good time to make offers below asking price');
    } else if (trends.price_trend === 'rising') {
        advice.push('🚀 <strong>Seller\'s market</strong> - Prices are rising, act quickly');
        advice.push('💨 Consider offering closer to asking price to secure the item');
    } else {
        advice.push('⚖️ <strong>Stable market</strong> - Standard negotiation tactics apply');
    }
    
    // Demand advice
    if (trends.demand_surge) {
        advice.push('🔥 <strong>High demand detected</strong> - Multiple buyers likely interested');
        advice.push('⚡ Make competitive offers quickly to avoid losing out');
    } else if (trends.hype_score < 0.3) {
        advice.push('😴 <strong>Low demand</strong> - Sellers may be more flexible');
        advice.push('🎯 Good opportunity for lower offers');
    }
    
    // Seasonal advice
    if (trends.seasonal_factor > 1.1) {
        advice.push('❄️ <strong>Peak season pricing</strong> - Expect 15-25% premium');
        advice.push('📅 Consider waiting for off-season if not urgent');
    } else if (trends.seasonal_factor < 0.9) {
        advice.push('🌞 <strong>Off-season advantage</strong> - Prices typically 10-20% lower');
        advice.push('💰 Great time to buy, sellers want to clear inventory');
    }
    
    // Data quality advice
    if (trends.data_sources && trends.data_sources >= 2) {
        advice.push('📊 <strong>High confidence</strong> - Analysis based on multiple data sources');
    } else {
        advice.push('⚠️ <strong>Limited data</strong> - Use these insights as rough guidance');
    }
    
    return advice;
}

autoFillFromScan(estimatedPrice) {
    const priceInput = document.getElementById('price');
    
    if (!priceInput.value) {
        // If no price set, use estimated market price
        priceInput.value = estimatedPrice.toFixed(2);
        this.showToast('💡 Price auto-filled from market data', 'success');
    } else {
        // If price already set, show comparison
        const currentPrice = parseFloat(priceInput.value);
        const difference = ((currentPrice - estimatedPrice) / estimatedPrice * 100).toFixed(1);
        
        if (difference > 10) {
            this.showToast(`⚠️ Your price is ${difference}% above market average`, 'warning');
        } else if (difference < -10) {
            this.showToast(`💰 Your price is ${Math.abs(difference)}% below market average`, 'success');
        } else {
            this.showToast(`✅ Your price is close to market average`, 'success');
        }
    }
    
    // Trigger price indicator update
    priceInput.dispatchEvent(new Event('input'));
    this.triggerHaptic();
}

watchMarket(itemName) {
    // Add to watched items (stored in localStorage)
    let watchedItems = JSON.parse(localStorage.getItem('watchedMarkets') || '[]');
    
    if (!watchedItems.includes(itemName)) {
        watchedItems.push(itemName);
        localStorage.setItem('watchedMarkets', JSON.stringify(watchedItems));
        
        this.showToast(`👀 Now watching market for "${itemName}"`, 'success');
        
        // Set up periodic checking (every 30 minutes)
        this.scheduleMarketCheck(itemName);
    } else {
        this.showToast(`Already watching "${itemName}"`, 'info');
    }
    
    this.triggerHaptic();
}

scheduleMarketCheck(itemName) {
    // This would normally set up background checking
    // For demo purposes, just show what would happen
    setTimeout(() => {
        this.showToast(`📊 Market update: Checking ${itemName} trends...`, 'info');
    }, 5000);
}

updatePriceIndicatorFromScan(userPrice, marketPrice) {
    const indicator = document.getElementById('priceIndicator');
    if (!indicator) return;
    
    const difference = ((userPrice - marketPrice) / marketPrice * 100);
    
    if (difference > 20) {
        indicator.textContent = `📈 ${difference.toFixed(0)}% above market average`;
        indicator.className = 'price-status overpriced';
    } else if (difference > 10) {
        indicator.textContent = `📊 ${difference.toFixed(0)}% above market average`;
        indicator.className = 'price-status market-price';
    } else if (difference < -20) {
        indicator.textContent = `💰 ${Math.abs(difference).toFixed(0)}% below market average - Great deal!`;
        indicator.className = 'price-status good-deal';
    } else if (difference < -10) {
        indicator.textContent = `💰 ${Math.abs(difference).toFixed(0)}% below market average`;
        indicator.className = 'price-status good-deal';
    } else {
        indicator.textContent = `✅ Close to market average`;
        indicator.className = 'price-status market-price';
    }
}
function renderResults(results, occasion, userName) {
  const section = document.getElementById('results-section');
  const noResults = document.getElementById('no-results');
  const grid = document.getElementById('results-grid');
  const title = document.getElementById('results-title');

  if (!results || results.length === 0) {
    section.classList.add('hidden');
    noResults.classList.remove('hidden');
    return;
  }

  noResults.classList.add('hidden');
  section.classList.remove('hidden');
  title.textContent = `✨ ${results.length} outfits found for ${userName}'s ${occasion}`;

  grid.innerHTML = results.map(item => `
    <div class="product-card">

      <!-- 🔥 IMAGE ADDED HERE -->
      <img src="https://source.unsplash.com/300x300/?indian-outfit"
           style="width:100%; border-radius:10px; margin-bottom:10px;" />

      <span class="platform-badge platform-${item.platform}">${item.platform}</span>

      <div class="product-name">${item.name}</div>
      <div class="product-cat">${item.category} · ${item.color} · Size ${item.size}</div>

      <div class="product-meta">
        <div class="meta-row">
          <span class="meta-label">Price</span>
          <span class="meta-value price-value">₹${item.price.toLocaleString('en-IN')}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Quality</span>
          <span class="meta-value">${renderStars(item.quality_rating)} ${item.quality_rating}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Delivery</span>
          <span class="meta-value">🚚 ${item.delivery_days} days</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Occasion</span>
          <span class="meta-value">${item.occasion}</span>
        </div>
      </div>

      <button class="btn-buy" id="buy-${item.id}" onclick="logPurchase(${item.id})">
        🛍️ Add to Wardrobe
      </button>
    </div>
  `).join('');
}

// ── Section Navigation ──────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  const idx = ['home', 'recommend', 'history'].indexOf(name);
  document.querySelectorAll('.nav-btn')[idx].classList.add('active');

  if (name === 'history') loadHistory();
}

// ── Checkbox styling ─────────────────────────────────────────────
document.querySelectorAll('.check-item').forEach(item => {
  item.addEventListener('click', () => item.classList.toggle('selected'));
});

// ── Load saved profile into form ─────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  fetch('/api/history').then(r => r.json()).then(data => {
    // silently preload
  }).catch(() => {});

  // try prefill profile form if profile exists (optional enhancement)
});

// ── Save Profile ─────────────────────────────────────────────────
async function saveProfile(e) {
  e.preventDefault();
  const status = document.getElementById('profile-status');

  const interests = [...document.querySelectorAll('.check-item.selected')]
    .map(el => el.querySelector('input').value);

  const budgetMin = parseInt(document.getElementById('budget_min').value);
  const budgetMax = parseInt(document.getElementById('budget_max').value);

  if (budgetMin >= budgetMax) {
    showStatus(status, 'Budget Max must be greater than Budget Min!', 'error');
    return;
  }
  if (interests.length === 0) {
    showStatus(status, 'Please select at least one style interest!', 'error');
    return;
  }

  const payload = {
    name: document.getElementById('name').value.trim(),
    age: document.getElementById('age').value,
    gender: document.getElementById('gender').value,
    body_type: document.getElementById('body_type').value,
    skin_tone: document.getElementById('skin_tone').value,
    size: document.getElementById('size').value,
    budget_min: budgetMin,
    budget_max: budgetMax,
    interests
  };

  try {
    const res = await fetch('/api/save-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showStatus(status, `✅ ${data.message}`, 'success');
      setTimeout(() => showSection('recommend'), 1200);
    } else {
      showStatus(status, `❌ ${data.message}`, 'error');
    }
  } catch (err) {
    showStatus(status, '❌ Could not connect to server.', 'error');
  }
}

function showStatus(el, msg, type) {
  el.textContent = msg;
  el.className = `profile-status ${type}`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 4000);
}

// ── Get Recommendations ───────────────────────────────────────────
let priceChartInstance = null;
let qualityChartInstance = null;

async function getRecommendations() {
  const occasion = document.getElementById('occasion').value;
  const sort_by = document.getElementById('sort_by').value;

  if (!occasion) {
    alert('Please select an occasion first!');
    return;
  }

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ occasion, sort_by })
    });
    const data = await res.json();

    if (!data.success) {
      alert(data.message);
      return;
    }

    renderCharts(data.price_chart, data.quality_chart);
    renderResults(data.results, occasion, data.user);

  } catch (err) {
    alert('Could not connect to server. Make sure Flask is running!');
  }
}

function renderCharts(priceData, qualityData) {
  document.getElementById('charts-section').classList.remove('hidden');

  const platforms = Object.keys(priceData);
  const colors = { Myntra: '#FF3F6C', Meesho: '#9B1FFF', Amazon: '#FF9900' };
  const bgColors = platforms.map(p => colors[p] || '#888');

  if (priceChartInstance) priceChartInstance.destroy();
  if (qualityChartInstance) qualityChartInstance.destroy();

  priceChartInstance = new Chart(document.getElementById('priceChart'), {
    type: 'bar',
    data: {
      labels: platforms,
      datasets: [{
        label: 'Avg Price (₹)',
        data: Object.values(priceData),
        backgroundColor: bgColors,
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => '₹' + v } }
      }
    }
  });

  qualityChartInstance = new Chart(document.getElementById('qualityChart'), {
    type: 'bar',
    data: {
      labels: platforms,
      datasets: [{
        label: 'Avg Quality (/5)',
        data: Object.values(qualityData),
        backgroundColor: bgColors,
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 5, ticks: { stepSize: 1 } }
      }
    }
  });
}

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

function renderStars(rating) {
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5 ? 1 : 0;
  return '<span class="stars">' + '★'.repeat(full) + (half ? '½' : '') + '</span>';
}

// ── Log Purchase ──────────────────────────────────────────────────
async function logPurchase(itemId) {
  try {
    const res = await fetch('/api/log-purchase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId })
    });
    const data = await res.json();
    if (data.success) {
      const btn = document.getElementById(`buy-${itemId}`);
      btn.textContent = '✅ Added!';
      btn.classList.add('logged');
      btn.disabled = true;
    }
  } catch (err) {
    alert('Could not log purchase.');
  }
}

// ── Load History ──────────────────────────────────────────────────
let historyChartInstance = null;

async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();

    const grid = document.getElementById('history-grid');
    const noHistory = document.getElementById('no-history');
    const statsCard = document.getElementById('stats-chart-card');

    if (!data.items || data.items.length === 0) {
      grid.innerHTML = '';
      noHistory.classList.remove('hidden');
      statsCard.classList.add('hidden');
      return;
    }

    noHistory.classList.add('hidden');
    statsCard.classList.remove('hidden');

    // Render pie chart
    if (historyChartInstance) historyChartInstance.destroy();
    const stats = data.stats;
    historyChartInstance = new Chart(document.getElementById('historyChart'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(stats),
        datasets: [{
          data: Object.values(stats),
          backgroundColor: ['#FF6B00','#D4A017','#8B1A1A','#9B1FFF','#FF3F6C','#FF9900'],
          borderWidth: 2,
          borderColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } }
      }
    });

    // Render history cards
    grid.innerHTML = data.items.map(item => `
      <div class="product-card">
        <span class="platform-badge platform-${item.platform}">${item.platform}</span>
        <div class="product-name">${item.name}</div>
        <div class="product-cat">${item.category} · ${item.color}</div>
        <div class="product-meta">
          <div class="meta-row">
            <span class="meta-label">Paid</span>
            <span class="meta-value price-value">₹${parseInt(item.price).toLocaleString('en-IN')}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Quality</span>
            <span class="meta-value">${renderStars(parseFloat(item.quality_rating))} ${item.quality_rating}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Occasion</span>
            <span class="meta-value">${item.occasion}</span>
          </div>
        </div>
      </div>
    `).join('');

  } catch (err) {
    console.error('Error loading history:', err);
  }
}

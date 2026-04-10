function showSection(name) {
  document.querySelectorAll('.section').forEach((section) => section.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach((button) => button.classList.remove('active'));
  document.getElementById(name).classList.add('active');

  const idx = ['home', 'recommend', 'history'].indexOf(name);
  if (idx >= 0) {
    document.querySelectorAll('.nav-btn')[idx].classList.add('active');
  }

  if (name === 'history') {
    loadHistory();
  }
}

function syncInterestSelection(label) {
  const input = label.querySelector('input[type="checkbox"]');
  label.classList.toggle('selected', Boolean(input && input.checked));
}

document.querySelectorAll('.check-item').forEach((item) => {
  const input = item.querySelector('input[type="checkbox"]');
  if (!input) {
    return;
  }

  item.addEventListener('click', (event) => {
    event.preventDefault();
    input.checked = !input.checked;
    syncInterestSelection(item);
  });

  input.addEventListener('change', () => syncInterestSelection(item));
  syncInterestSelection(item);
});

window.addEventListener('DOMContentLoaded', () => {
  fetch('/api/history').catch(() => {});
  loadSavedProfile();
});

async function saveProfile(event) {
  event.preventDefault();
  const status = document.getElementById('profile-status');

  const interests = [...document.querySelectorAll('.check-item input:checked')].map((input) => input.value);
  const budgetMin = parseInt(document.getElementById('budget_min').value, 10);
  const budgetMax = parseInt(document.getElementById('budget_max').value, 10);

  if (budgetMin >= budgetMax) {
    showStatus(status, 'Budget Max must be greater than Budget Min.', 'error');
    return;
  }

  if (interests.length === 0) {
    showStatus(status, 'Please select at least one style interest.', 'error');
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
    interests,
  };

  try {
    const response = await fetch('/api/save-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (data.success) {
      showStatus(status, data.message, 'success');
      setTimeout(() => showSection('recommend'), 1000);
      return;
    }

    showStatus(status, data.message, 'error');
  } catch (error) {
    showStatus(status, 'Could not connect to the server.', 'error');
  }
}

function showStatus(element, message, type) {
  element.textContent = message;
  element.className = `profile-status ${type}`;
  element.classList.remove('hidden');
  setTimeout(() => element.classList.add('hidden'), 3500);
}

async function loadSavedProfile() {
  try {
    const response = await fetch('/api/profile');
    const data = await response.json();
    if (data.success && data.profile) {
      populateProfileForm(data.profile);
    }
  } catch (error) {
    console.error('Could not load saved profile:', error);
  }
}

function populateProfileForm(profile) {
  [
    'name',
    'age',
    'gender',
    'body_type',
    'skin_tone',
    'size',
    'budget_min',
    'budget_max',
  ].forEach((id) => {
    const field = document.getElementById(id);
    if (field && profile[id] !== undefined && profile[id] !== null) {
      field.value = profile[id];
    }
  });

  const selectedInterests = new Set(profile.interests || []);
  document.querySelectorAll('.check-item').forEach((item) => {
    const input = item.querySelector('input[type="checkbox"]');
    if (!input) {
      return;
    }
    input.checked = selectedInterests.has(input.value);
    syncInterestSelection(item);
  });
}

let historyChartInstance = null;
let currentRecommendationItems = {};

async function getRecommendations() {
  const occasion = document.getElementById('occasion').value;
  const sortBy = document.getElementById('sort_by').value;

  if (!occasion) {
    alert('Please select an occasion first.');
    return;
  }

  try {
    const response = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ occasion, sort_by: sortBy }),
    });
    const data = await response.json();

    if (!data.success) {
      alert(data.message);
      return;
    }

    renderResults(data.results, occasion, data.user);
  } catch (error) {
    alert('Could not connect to the server. Make sure Flask is running.');
  }
}

function renderResults(results, occasion, userName) {
  const section = document.getElementById('results-section');
  const noResults = document.getElementById('no-results');
  const grid = document.getElementById('results-grid');
  const title = document.getElementById('results-title');

  currentRecommendationItems = Object.fromEntries((results || []).map((item) => [String(item.id), item]));

  if (!results || results.length === 0) {
    section.classList.add('hidden');
    noResults.classList.remove('hidden');
    return;
  }

  noResults.classList.add('hidden');
  section.classList.remove('hidden');
  title.textContent = `${results.length} outfits found for ${userName}'s ${occasion}`;

  grid.innerHTML = results.map((item) => `
    <div class="product-card">
      <img
        class="product-image"
        src="${escapeHtml(getProductImage(item))}"
        data-fallback="${escapeHtml(buildProductImage(item))}"
        alt="${escapeHtml(item.name)}"
        loading="lazy"
      />
      <span class="platform-badge platform-${sanitizeClassName(item.platform)}">${escapeHtml(item.platform)}</span>
      <div class="product-name">${getProductNameMarkup(item)}</div>
      <div class="product-cat">${escapeHtml(item.category)} · ${escapeHtml(item.color)} · Size ${escapeHtml(item.size)}</div>
      <div class="match-badge">${escapeHtml(getMatchBadgeText(item))}</div>
      <div class="product-meta">
        <div class="meta-row">
          <span class="meta-label">Price</span>
          <span class="meta-value price-value">Rs ${Number(item.price).toLocaleString('en-IN')}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Quality</span>
          <span class="meta-value">${renderStars(item.quality_rating)} ${item.quality_rating}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Delivery</span>
          <span class="meta-value">${escapeHtml(String(item.delivery_days))} days</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Occasion</span>
          <span class="meta-value">${escapeHtml(item.occasion)}</span>
        </div>
      </div>
      <button class="btn-buy" id="buy-${String(item.id)}" onclick='logPurchase(${JSON.stringify(String(item.id))})'>
        Add to Wardrobe
      </button>
    </div>
  `).join('');

  attachImageFallbacks(grid);
}

function renderStars(rating) {
  const full = Math.floor(Number(rating) || 0);
  const half = (Number(rating) || 0) % 1 >= 0.5 ? 1 : 0;
  return `<span class="stars">${'★'.repeat(full)}${half ? '½' : ''}</span>`;
}

async function logPurchase(itemId) {
  try {
    const item = currentRecommendationItems[String(itemId)] || null;
    const response = await fetch('/api/log-purchase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId, item }),
    });
    const data = await response.json();

    if (data.success) {
      const button = document.getElementById(`buy-${itemId}`);
      if (button) {
        button.textContent = 'Added';
        button.classList.add('logged');
        button.disabled = true;
      }
    }
  } catch (error) {
    alert('Could not save this item.');
  }
}

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    const data = await response.json();

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

    if (historyChartInstance) {
      historyChartInstance.destroy();
    }

    historyChartInstance = new Chart(document.getElementById('historyChart'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(data.stats),
        datasets: [{
          data: Object.values(data.stats),
          backgroundColor: ['#35261b', '#8a6332', '#b2405a', '#c49558', '#70645b', '#d3b07a'],
          borderWidth: 2,
          borderColor: '#f4ede3',
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
      },
    });

    grid.innerHTML = data.items.map((item) => `
      <div class="product-card">
        <img
          class="product-image"
          src="${escapeHtml(getProductImage(item))}"
          data-fallback="${escapeHtml(buildProductImage(item))}"
          alt="${escapeHtml(item.name)}"
          loading="lazy"
        />
        <span class="platform-badge platform-${sanitizeClassName(item.platform)}">${escapeHtml(item.platform)}</span>
        <div class="product-name">${getProductNameMarkup(item)}</div>
        <div class="product-cat">${escapeHtml(item.category)} · ${escapeHtml(item.color || 'Assorted')}</div>
        <div class="product-meta">
          <div class="meta-row">
            <span class="meta-label">Paid</span>
            <span class="meta-value price-value">Rs ${Number(item.price || 0).toLocaleString('en-IN')}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Quality</span>
            <span class="meta-value">${renderStars(item.quality_rating)} ${item.quality_rating}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Occasion</span>
            <span class="meta-value">${escapeHtml(item.occasion || 'Saved Item')}</span>
          </div>
        </div>
      </div>
    `).join('');

    attachImageFallbacks(grid);
  } catch (error) {
    console.error('Error loading history:', error);
  }
}

function attachImageFallbacks(scope) {
  scope.querySelectorAll('.product-image').forEach((img) => {
    img.addEventListener('error', () => {
      const fallback = img.dataset.fallback;
      if (fallback && img.src !== fallback) {
        img.src = fallback;
      }
    }, { once: true });
  });
}

function getProductImage(item) {
  if (!item.image_url) {
    return buildProductImage(item);
  }

  if (/^https?:\/\//i.test(item.image_url)) {
    return `/api/image-proxy?url=${encodeURIComponent(item.image_url)}`;
  }

  return item.image_url;
}

function getProductNameMarkup(item) {
  const name = escapeHtml(item.name);
  if (!item.product_url) {
    return name;
  }
  return `<a class="product-link" href="${escapeHtml(item.product_url)}" target="_blank" rel="noreferrer">${name}</a>`;
}

function getMatchBadgeText(item) {
  return item.match_reason || 'Saved item';
}

function buildProductImage(item) {
  const palette = {
    Red: '#9e3f3f',
    Blue: '#43578d',
    Green: '#58745f',
    Beige: '#b79d81',
    Pink: '#b26f87',
    Orange: '#b86e35',
    Purple: '#67548f',
    Yellow: '#b2914c',
    White: '#e6e1da',
    Cream: '#ede1c5',
    Gold: '#b38a48',
    Navy: '#2f4560',
    Maroon: '#6e3342',
    Grey: '#6e706f',
    Black: '#3a3838',
  };

  const accent = palette[item.color] || '#8a6332';
  const textColor = accent === '#e6e1da' || accent === '#ede1c5' ? '#2d241b' : '#ffffff';
  const category = escapeHtml(item.category || 'Outfit');
  const name = escapeHtml(item.name || 'Style Pick');
  const color = escapeHtml(item.color || 'Classic');

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220" role="img" aria-label="${name}">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#f8f2ea"/>
          <stop offset="100%" stop-color="#efe3d2"/>
        </linearGradient>
      </defs>
      <rect width="320" height="220" rx="20" fill="url(#bg)"/>
      <circle cx="250" cy="48" r="54" fill="${accent}" opacity="0.18"/>
      <circle cx="82" cy="178" r="64" fill="${accent}" opacity="0.12"/>
      <rect x="20" y="18" width="90" height="28" rx="14" fill="${accent}"/>
      <text x="65" y="37" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" fill="${textColor}">${color}</text>
      <path d="M110 70 L145 52 L175 52 L210 70 L193 96 L193 170 L127 170 L127 96 Z" fill="${accent}" opacity="0.94"/>
      <path d="M135 52 Q160 30 185 52" fill="none" stroke="#6b4c31" stroke-width="5" stroke-linecap="round"/>
      <path d="M127 96 L108 78" fill="none" stroke="${accent}" stroke-width="18" stroke-linecap="round"/>
      <path d="M193 96 L212 78" fill="none" stroke="${accent}" stroke-width="18" stroke-linecap="round"/>
      <text x="24" y="194" font-size="16" font-weight="700" font-family="Arial, sans-serif" fill="#4a3425">${category}</text>
      <text x="24" y="212" font-size="14" font-family="Arial, sans-serif" fill="#6a5645">${name}</text>
    </svg>
  `.trim();

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function sanitizeClassName(value) {
  return String(value || '').replace(/[^a-z0-9_-]/gi, '');
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

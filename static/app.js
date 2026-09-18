const state = { mode: 'login', pendingVerification: false };
const grid = document.querySelector('#restaurant-grid');
const emptyState = document.querySelector('#empty-state');
const count = document.querySelector('#result-count');
const toast = document.querySelector('#toast');
const modal = document.querySelector('#auth-modal');
const authForm = document.querySelector('#auth-form');

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2800);
}

function restaurantCard(item, index) {
  return `<article class="restaurant-card" style="animation-delay:${index * 50}ms"><div class="card-image" style="background:${item.color}"><button class="favorite ${item.is_favorite ? 'saved' : ''}" data-favorite="${item.id}" aria-label="Save ${item.name}">${item.is_favorite ? '♥' : '♡'}</button></div><div class="card-body"><div class="card-top"><span class="card-title">${item.name}</span><span class="rating">★ ${item.rating}</span></div><div class="card-meta">${item.cuisine} · ${item.neighborhood} · ${item.distance} · ${item.price}</div><div class="card-tags">${item.tags.map(tag => `<span>${tag}</span>`).join('')}</div></div></article>`;
}

async function loadRestaurants() {
  const params = new URLSearchParams({ q: document.querySelector('#search-input').value, cuisine: document.querySelector('#cuisine-filter').value, sort: document.querySelector('#sort-filter').value });
  const response = await fetch(`/api/restaurants?${params}`);
  const data = await response.json();
  count.textContent = `${data.count} ${data.count === 1 ? 'place' : 'places'} found`;
  grid.innerHTML = data.restaurants.map(restaurantCard).join('');
  emptyState.hidden = data.restaurants.length > 0;
}

async function refreshSession() {
  const response = await fetch('/api/session');
  const data = await response.json();
  document.querySelector('#account-button').textContent = data.user ? data.user.name.split(' ')[0] : 'Sign in';
  await loadRestaurants();
}

function openAuth() {
  modal.hidden = false;
  document.querySelector('#form-message').textContent = '';
  updateAuthView();
}

function updateAuthView() {
  const register = state.mode === 'register';
  const verify = state.mode === 'verify';
  document.querySelector('[name="email"]').required = !verify;
  document.querySelector('[name="password"]').required = !verify;
  document.querySelector('[name="code"]').required = verify;
  document.querySelector('#auth-title').textContent = verify ? 'Check your inbox.' : register ? 'Make room for more.' : 'Welcome back.';
  document.querySelector('#auth-copy').textContent = verify ? 'For this demo, your verification code is shown after registration.' : register ? 'Create a private list of places worth remembering.' : 'Save the spots you want to come back to.';
  document.querySelector('#name-field').hidden = !register;
  document.querySelector('#code-field').hidden = !verify;
  document.querySelector('[name="email"]').hidden = verify;
  document.querySelector('[name="password"]').hidden = verify;
  document.querySelector('#auth-submit').textContent = verify ? 'Verify email' : register ? 'Create account' : 'Sign in';
  document.querySelector('#auth-switch').hidden = verify;
  document.querySelector('#auth-switch').textContent = register ? 'Already have an account? Sign in' : 'New here? Create an account';
}

document.querySelector('#search-form').addEventListener('submit', event => { event.preventDefault(); loadRestaurants(); document.querySelector('#discover').scrollIntoView({ behavior: 'smooth' }); });
document.querySelector('#cuisine-filter').addEventListener('change', loadRestaurants);
document.querySelector('#sort-filter').addEventListener('change', loadRestaurants);
document.querySelectorAll('.quick-tags button').forEach(button => button.addEventListener('click', () => { document.querySelector('#search-input').value = button.dataset.query; loadRestaurants(); document.querySelector('#discover').scrollIntoView({ behavior: 'smooth' }); }));
document.querySelector('#account-button').addEventListener('click', openAuth);
document.querySelector('#close-modal').addEventListener('click', () => { modal.hidden = true; });
document.querySelector('#auth-switch').addEventListener('click', () => { state.mode = state.mode === 'register' ? 'login' : 'register'; updateAuthView(); });

authForm.addEventListener('submit', async event => {
  event.preventDefault();
  const formData = new FormData(authForm);
  const payload = Object.fromEntries(formData.entries());
  const endpoint = state.mode === 'verify' ? '/api/verify' : state.mode === 'register' ? '/api/register' : '/api/login';
  const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await response.json();
  const message = document.querySelector('#form-message');
  if (!response.ok) {
    message.textContent = data.error;
    if (data.needs_verification) { state.mode = 'verify'; updateAuthView(); }
    return;
  }
  if (state.mode === 'register') {
    message.textContent = `Demo code: ${data.demo_code}`;
    state.mode = 'verify';
    updateAuthView();
    return;
  }
  modal.hidden = true;
  showToast(data.message);
  await refreshSession();
});

grid.addEventListener('click', async event => {
  const button = event.target.closest('[data-favorite]');
  if (!button) return;
  const response = await fetch(`/api/favorites/${button.dataset.favorite}`, { method: 'POST' });
  const data = await response.json();
  if (response.status === 401) { openAuth(); return; }
  if (!response.ok) { showToast(data.error); return; }
  showToast(data.saved ? 'Saved to your table list.' : 'Removed from your table list.');
  await loadRestaurants();
});

refreshSession();

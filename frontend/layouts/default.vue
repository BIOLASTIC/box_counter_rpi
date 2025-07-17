<template>
  <div>
    <!-- Real-Time Top Bar -->
    <div class="top-bar d-flex justify-content-between align-items-center">
        <div class="left-icons d-flex align-items-center gap-3">
            <span data-bs-toggle="tooltip" :title="topBar.internet_active ? `Internet OK (IP: ${topBar.ip_address})` : 'No Internet Access'">
                <i class="status-icon" :class="topBar.internet_active ? 'bi-cloud-check-fill text-success' : 'bi-cloud-slash'"></i>
            </span>
            <span data-bs-toggle="tooltip" title="Ethernet">
                <i class="status-icon bi-ethernet" :class="{ 'active': topBar.eth_active }"></i>
            </span>
            <span data-bs-toggle="tooltip" :title="topBar.wifi_active ? `Connected to: ${topBar.wifi_ssid}` : 'WiFi Disconnected'">
                <i class="status-icon" :class="wifiIconClass"></i>
                <span v-if="topBar.wifi_active" class="status-text">{{ topBar.wifi_strength }}%</span>
            </span>
            <span data-bs-toggle="tooltip" :title="bleTooltip">
                <i class="status-icon bi-bluetooth" :class="bleIconClass"></i>
            </span>
        </div>
        <div class="right-time d-flex gap-3">
            <span id="live-date"></span>
            <span id="live-time"></span>
        </div>
    </div>

    <!-- Main Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <!-- ... Navbar content ... -->
    </nav>
    
    <!-- Page Content -->
    <main class="container-fluid p-4">
      <slot /> <!-- This is where Nuxt will render the current page -->
    </main>
  </div>
</template>

<script setup>
import { useApplicationStore } from '~/stores/state';
import { computed, onMounted } from 'vue';

const store = useApplicationStore();
const topBar = computed(() => store.top_bar);

// Client-side only logic
onMounted(() => {
  // Initialize Bootstrap Tooltips
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

  // Real-time Clock
  function updateClock() {
      const now = new Date();
      document.getElementById('live-time').textContent = now.toLocaleTimeString();
      document.getElementById('live-date').textContent = now.toLocaleDateString();
  }
  updateClock();
  setInterval(updateClock, 1000);
});

// Computed properties for dynamic classes
const wifiIconClass = computed(() => {
  if (!topBar.value.wifi_active) return 'bi-wifi-off';
  if (topBar.value.wifi_strength > 75) return 'bi-wifi active';
  if (topBar.value.wifi_strength > 40) return 'bi-wifi-2 active';
  return 'bi-wifi-1 active';
});

const bleIconClass = computed(() => {
  if (topBar.value.ble_connected) return 'text-success';
  if (topBar.value.ble_saved) return 'text-primary';
  return '';
});

const bleTooltip = computed(() => {
    if (topBar.value.ble_connected) return 'Printer Connected';
    if (topBar.value.ble_saved) return 'Printer Saved (Disconnected)';
    return 'No Printer Saved';
});
</script>

<style>
/* Add the same global CSS from your old base.html here */
body { transition: background-color 0.3s, color 0.3s; }
.top-bar { background-color: #000 !important; color: #ccc !important; padding: 4px 12px; font-family: monospace; font-size: 1rem; }
.status-icon { font-size: 1.2rem; color: #6c757d; transition: color 0.5s ease-in-out; vertical-align: middle; }
.status-text { color: #999; margin-left: 2px; font-size: 0.9rem; vertical-align: middle; }
.status-icon.active { color: #0dcaf0; }
.status-icon.text-success { color: #198754 !important; }
.status-icon.text-primary { color: #0d6efd !important; }
</style>
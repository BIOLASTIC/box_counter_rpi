<template>
  <div class="row g-4 justify-content-center">
    <div class="col-lg-11 col-xl-10">
      <!-- Live Status Cards -->
      <div class="row g-4 text-center">
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 text-white" style="background-color: #007bff;">
            <h3 class="card-title">LIVE COUNT</h3>
            <p class="display-1">{{ status.object_count }} / {{ status.batch_target }}</p>
          </div>
        </div>
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 text-white" style="background-color: #6f42c1;">
            <h3 class="card-title">GATE STATUS</h3>
            <p class="display-1" :class="{ 'text-warning': status.gate_status !== 'Open' }">
              {{ status.gate_status.toUpperCase() }}
            </p>
          </div>
        </div>
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 text-white" style="background-color: #198754;">
            <h3 class="card-title">BATCHES COMPLETED</h3>
            <p class="display-1">{{ status.batches_completed }}</p>
          </div>
        </div>
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 text-white" style="background-color: #dc3545;">
            <h3 class="card-title">IR SENSOR</h3>
            <p class="display-4" :class="{ 'text-warning': status.ir_status === 'Blocked' }">
              {{ status.ir_status.toUpperCase() }}
            </p>
          </div>
        </div>
        <div class="col-lg-8">
          <div class="card p-3 h-100 text-white" style="background-color: #6c757d;">
            <h3 class="card-title">LAST PRINTED DATA</h3>
            <p class="display-4 font-monospace" style="word-wrap: break-word;">
              {{ status.last_printed_payload }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- System Status -->
      <div class="card mt-4">
        <div class="card-body p-3 text-center">
            <h3 class="card-title text-muted">SYSTEM STATUS</h3>
            <div class="mt-2">
                <span class="badge fs-4" :class="systemStatusClass">{{ status.system_status }}</span>
            </div>
        </div>
      </div>

      <!-- Set New Configuration Card -->
      <div class="card mt-4">
          <!-- Form and logic as implemented previously -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { useApplicationStore } from '~/stores/state';
import { computed } from 'vue';

const store = useApplicationStore();
const status = computed(() => store.status);

const systemStatusClass = computed(() => {
    const s = status.value.system_status;
    if (s.includes('Ready')) return 'bg-success';
    if (s.includes('Counting')) return 'bg-info text-dark';
    if (s.includes('Waiting') || s.includes('Closing')) return 'bg-warning text-dark';
    return 'bg-secondary';
});

// You would add the <script> logic for form handling here,
// similar to the previous Vue example.
</script>

<style scoped>
.card-title { color: rgba(255, 255, 255, 0.7); }
.display-1, .display-4 { font-weight: bold; }
</style>
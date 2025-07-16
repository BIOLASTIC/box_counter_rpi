<template>
  <div class="row g-4 justify-content-center">
    <div class="col-lg-11 col-xl-10">
      <!-- Live Status Cards -->
      <div class="row g-4 text-center">
        <!-- Live Count -->
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 dashboard-card text-white" style="background-color: #007bff;">
            <h3 class="card-title">LIVE COUNT</h3>
            <p class="display-1">{{ store.status.object_count }} / {{ store.status.batch_target }}</p>
          </div>
        </div>
        <!-- Gate Status -->
        <div class="col-md-6 col-lg-4">
          <div class="card p-3 h-100 dashboard-card text-white" style="background-color: #6f42c1;">
            <h3 class="card-title">GATE STATUS</h3>
            <p class="display-1" :class="store.status.gate_status === 'Open' ? 'text-white' : 'text-warning'">
              {{ store.status.gate_status.toUpperCase() }}
            </p>
          </div>
        </div>
        <!-- And so on for the other cards... -->
      </div>

      <!-- Set New Configuration Card -->
      <div class="card mt-4">
          <div class="card-body p-4">
              <h2 class="card-title mb-4"><i class="bi bi-pencil-square"></i> Set New Configuration</h2>
              <form @submit.prevent="updateConfig">
                  <!-- Form inputs -->
                  <div class="row">
                      <div class="col-md-6 mb-3">
                          <label for="batch_target" class="form-label">New Batch Target</label>
                          <input v-model="form.batch_target" type="number" class="form-control form-control-lg" id="batch_target" required>
                      </div>
                      <div class="col-md-6 mb-3">
                          <label for="gate_wait_time" class="form-label">New Gate Wait Time (s)</label>
                          <input v-model="form.gate_wait_time" type="number" class="form-control form-control-lg" id="gate_wait_time" required>
                      </div>
                  </div>
                  <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-2">
                      <button @click="resetCounter" type="button" class="btn btn-danger btn-lg">Reset Live Count</button>
                      <button type="submit" class="btn btn-primary btn-lg">Update Configuration</button>
                  </div>
              </form>
              <div v-if="message" class="alert mt-3" :class="message.success ? 'alert-success' : 'alert-danger'">
                {{ message.text }}
              </div>
          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles for this component */
.dashboard-card { border: none; }
.dashboard-card .card-title { color: rgba(255, 255, 255, 0.7); }
.dashboard-card .display-1 { font-weight: bold; }
</style>

<script setup>
import { useApplicationStore } from '~/stores/state';
import { ref, watch } from 'vue';

// Use our Pinia store to get reactive state
const store = useApplicationStore();

const form = ref({
  batch_target: 0,
  gate_wait_time: 0,
});

const message = ref(null);

// Watch for changes in the store and update the form's default values
watch(() => store.status, (newStatus) => {
  form.value.batch_target = newStatus.batch_target;
  form.value.gate_wait_time = newStatus.gate_wait_time;
}, { immediate: true });

function showMessage(text, success) {
  message.value = { text, success };
  setTimeout(() => {
    message.value = null;
  }, 3000);
}

// Function to send form data to the Flask API
async function updateConfig() {
  const formData = new FormData();
  formData.append('batch_target', form.value.batch_target);
  formData.append('gate_wait_time', form.value.gate_wait_time);

  try {
    const response = await $fetch('http://localhost:5000/api/set_config', {
      method: 'POST',
      body: formData,
    });
    showMessage(response.message, response.success);
  } catch (error) {
    showMessage('Failed to update configuration.', false);
  }
}

async function resetCounter() {
    if (confirm('Are you sure?')) {
        try {
            const response = await $fetch('http://localhost:5000/api/reset_counter', {
                method: 'POST',
            });
            showMessage(response.message, response.success);
        } catch (error) {
            showMessage('Failed to reset counter.', false);
        }
    }
}
</script>
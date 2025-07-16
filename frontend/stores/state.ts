import { defineStore } from 'pinia'

export const useApplicationStore = defineStore('application', {
  state: () => ({
    // For Dashboard
    status: {
      object_count: 0,
      batch_target: 0,
      gate_status: 'Initializing',
      ir_status: 'Initializing',
      system_status: 'Initializing',
      batches_completed: 0,
      last_printed_payload: 'N/A',
    },
    // For Diagnostics
    pins: {
      IR_SENSOR: 0,
      GATE_RELAY: 0,
      GREEN_LED: 0,
      RED_LED: 0,
      BUZZER: 0,
    },
    // For Top Bar
    top_bar: {
      internet_active: false,
      ip_address: 'N/A',
      eth_active: false,
      wifi_active: false,
      wifi_strength: 0,
      wifi_ssid: 'N/A',
      ble_saved: false,
      ble_connected: false,
    },
  }),
  actions: {
    // These actions are called by our WebSocket plugin to update the state
    setStatus(newStatus: any) {
      this.status = newStatus;
    },
    setPins(newPins: any) {
      this.pins = newPins;
    },
    setTopBar(newTopBar: any) {
      this.top_bar = newTopBar;
    }
  }
})
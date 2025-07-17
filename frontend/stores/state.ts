import { defineStore } from 'pinia'

// --- TypeScript Interfaces for Type Safety ---
// Defines the shape of the data for the main dashboard
interface AppStatus {
  object_count: number;
  batch_target: number;
  gate_status: string;
  ir_status: string;
  system_status: string;
  batches_completed: number;
  last_printed_payload: string;
}

// Defines the shape of the data for the top status bar
interface TopBarStatus {
  internet_active: boolean;
  ip_address: string;
  eth_active: boolean;
  wifi_active: boolean;
  wifi_strength: number;
  wifi_ssid: string;
  ble_saved: boolean;
  ble_connected: boolean;
}

// Defines the shape of the data for the diagnostics page
interface PinStatus {
  IR_SENSOR: number;
  GATE_RELAY: number;
  GREEN_LED: number;
  RED_LED: number;
  BUZZER: number;
}


// --- The Pinia Store Definition ---
export const useApplicationStore = defineStore('application', {
  // The 'state' function defines the initial state of your application.
  // These are the default values before the first WebSocket message is received.
  state: () => ({
    status: {
      object_count: 0,
      batch_target: 0,
      gate_status: 'Initializing',
      ir_status: 'Initializing',
      system_status: 'Connecting...',
      batches_completed: 0,
      last_printed_payload: 'N/A',
    } as AppStatus,

    top_bar: {
      internet_active: false,
      ip_address: 'N/A',
      eth_active: false,
      wifi_active: false,
      wifi_strength: 0,
      wifi_ssid: 'N/A',
      ble_saved: false,
      ble_connected: false,
    } as TopBarStatus,

    pins: {
      IR_SENSOR: 0,
      GATE_RELAY: 0,
      GREEN_LED: 0,
      RED_LED: 0,
      BUZZER: 0,
    } as PinStatus,
  }),

  // 'actions' are functions that can be called to modify the state.
  // Our WebSocket plugin will call these actions when it receives new data.
  actions: {
    /**
     * Updates the main dashboard status.
     * Merges new data with existing data to handle partial updates gracefully.
     */
    setStatus(newStatus: Partial<AppStatus>) {
      this.status = { ...this.status, ...newStatus };
    },

    /**
     * Updates the top bar status information.
     */
    setTopBar(newTopBar: TopBarStatus) {
      this.top_bar = newTopBar;
    },

    /**
     * Updates the live pin status for the diagnostics page.
     */
    setPins(newPins: PinStatus) {
      this.pins = newPins;
    }
  }
})
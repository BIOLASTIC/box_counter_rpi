/**
 * Virtual Keyboard: A robust and corrected version for the conveyor project.
 *
 * Solves two critical bugs:
 * 1. Dynamically adds padding to the page body to prevent the keyboard from
 *    hiding the active input field.
 * 2. Implements a dedicated, reliable listener for the 'Dismiss' button.
 */
class VirtualKeyboard {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error("Virtual keyboard container not found:", containerId);
            return;
        }
        this.currentInput = null;
        this.capsLock = false;
        this.keyboardHeight = 0; // Will store the keyboard's height

        this.keysLayout = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "backspace",
            "q", "w", "e", "r", "t", "y", "u", "i", "o", "p",
            "caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", "enter",
            "shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "?","@",
            "space", "dismiss"
        ];

        this._createKeyboard();
        this._attachEventListeners();
    }

    _createKeyboard() {
        this.keysContainer = document.createElement("div");
        this.keysContainer.classList.add("virtual-keyboard", "p-2", "d-flex", "flex-wrap", "justify-content-center");

        this.keysLayout.forEach(key => {
            const keyElement = document.createElement("button");
            keyElement.setAttribute("type", "button");
            // --- THE FIX: Use Bootstrap's btn-outline-secondary for auto theme switching ---
            keyElement.classList.add("btn", "btn-outline-secondary", "m-1");
            keyElement.style.width = "70px";
            keyElement.style.height = "70px";
            keyElement.style.fontSize = "1.2rem";
            keyElement.dataset.key = key.toLowerCase();

            switch (key) {
                // Special keys can have more specific colors
                case "backspace": keyElement.innerHTML = '<i class="bi bi-backspace-fill"></i>'; keyElement.classList.replace("btn-outline-secondary", "btn-warning"); break;
                case "caps": keyElement.innerHTML = '<i class="bi bi-capslock-fill"></i>'; keyElement.classList.replace("btn-outline-secondary", "btn-info"); break;
                case "space": keyElement.style.flexGrow = "5"; keyElement.innerHTML = 'SPACE'; break;
                case "dismiss": keyElement.innerHTML = '<i class="bi bi-x-circle-fill"></i>'; keyElement.classList.replace("btn-outline-secondary", "btn-danger"); break;
                case "enter": case "shift": keyElement.innerHTML = key.toUpperCase(); keyElement.classList.replace("btn-outline-secondary", "btn-info"); keyElement.style.width = "100px"; break;
                default: keyElement.textContent = key; break;
            }
            this.keysContainer.appendChild(keyElement);
        });
        
        this.container.appendChild(this.keysContainer);
    }

    _attachEventListeners() {
        // Delegated listener for all typing keys for efficiency
        this.keysContainer.addEventListener('click', (event) => {
            const keyButton = event.target.closest('button');
            if (!keyButton || !this.currentInput) return;

            const key = keyButton.dataset.key;
            if (key === "dismiss") return; // Dismiss is handled separately

            switch (key) {
                case "backspace": this.currentInput.value = this.currentInput.value.slice(0, -1); break;
                case "caps": this._toggleCapsLock(); break;
                case "space": this.currentInput.value += " "; break;
                case "enter": this.hide(); break;
                case "shift": break; // Placeholder
                default: this.currentInput.value += this.capsLock ? key.toUpperCase() : key.toLowerCase(); break;
            }
            this.currentInput.focus();
        });

        // --- FIX #1: DEDICATED AND RELIABLE DISMISS BUTTON ---
        // Find the dismiss button specifically and attach its own listener.
        const dismissButton = this.container.querySelector('[data-key="dismiss"]');
        if (dismissButton) {
            dismissButton.addEventListener('click', () => this.hide());
        }

        // Attach listeners to all designated input fields
        document.querySelectorAll('.virtual-keyboard-input').forEach(element => {
            element.addEventListener('focus', () => {
                this.show(element); // Pass the element being focused
            });
        });
    }
    
    _toggleCapsLock() {
        this.capsLock = !this.capsLock;
        this.keysContainer.querySelectorAll('[data-key]').forEach(keyEl => {
            if (keyEl.dataset.key.length === 1) {
                keyEl.textContent = this.capsLock ? keyEl.textContent.toUpperCase() : keyEl.textContent.toLowerCase();
            }
        });
    }

    show(element) {
        this.currentInput = element;
        this.container.style.display = "block";

        // --- FIX #2: DYNAMICALLY ADJUST PAGE TO PREVENT HIDING INPUT ---
        // A small timeout allows the browser to render the keyboard, so we can get its actual height.
        setTimeout(() => {
            // Get the actual height of the keyboard
            this.keyboardHeight = this.container.offsetHeight;
            
            // Add padding to the bottom of the body, creating space
            document.body.style.paddingBottom = this.keyboardHeight + 'px';
            
            // Now, scroll the focused element into view. It will have space to move into.
            element.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);
    }
    
    hide() {
        this.container.style.display = "none";
        
        // --- FIX #2 (Part 2): Remove the padding when keyboard is hidden ---
        document.body.style.paddingBottom = '0';
        
        if (this.currentInput) {
            this.currentInput.blur();
        }
        this.currentInput = null;
    }
}

// Initialize the keyboard once the DOM is fully loaded.
document.addEventListener('DOMContentLoaded', () => {
    new VirtualKeyboard('virtual-keyboard-container');
});
import { io } from 'socket.io-client'
import { useApplicationStore } from '../stores/state'

export default defineNuxtPlugin(() => {
  // Connect to the Flask-SocketIO server
  const socket = io('http://localhost:5001') 
  const store = useApplicationStore()

  socket.on('connect', () => {
    console.log('Socket.IO connected successfully!')
  })
  
  // Listen for the events we created in the backend
  socket.on('status_update', (data) => {
    store.setStatus(data)
  })

  socket.on('pin_update', (data) => {
    store.setPins(data)
  })

  socket.on('top_bar_update', (data) => {
    store.setTopBar(data)
  })

  return {
    provide: {
      socket,
    },
  }
})
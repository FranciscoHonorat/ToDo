import { createApp } from 'vue'
import App from './App.vue'
import { createHttpTaskApi } from './api/httpTaskApi'
import './style.css'

// Composition root do frontend: única parte que conhece a implementação HTTP.
createApp(App, { api: createHttpTaskApi('/api') }).mount('#app')

import './index.css'

import { createApp } from 'vue'
import { Button, FrappeUI, frappeRequest, setConfig } from 'frappe-ui'

import App from '@/App.vue'
import router from '@/router'
import { session } from '@/stores/session'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.component('Button', Button)
app.provide('session', session)
app.mount('#app')

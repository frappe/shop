import { createRouter, createWebHistory } from 'vue-router'

import { fetchOnboardingState } from '@/stores/onboarding'
import { session } from '@/stores/session'

const routes = [
	{
		path: '/onboarding',
		name: 'Onboarding',
		component: () => import('@/pages/Onboarding.vue'),
	},
	{
		path: '/',
		component: () => import('@/components/AppShell.vue'),
		children: [
			{ path: '', name: 'Dashboard', component: () => import('@/pages/Dashboard.vue') },
			{ path: 'orders', name: 'Orders', component: () => import('@/pages/Orders.vue') },
			{
				path: 'orders/:name',
				name: 'OrderDetail',
				component: () => import('@/pages/OrderDetail.vue'),
				props: true,
			},
			{ path: 'products', name: 'Products', component: () => import('@/pages/Products.vue') },
			{
				path: 'collections',
				name: 'Collections',
				component: () => import('@/pages/Collections.vue'),
			},
			{ path: 'settings', name: 'Settings', component: () => import('@/pages/Settings.vue') },
		],
	},
]

const router = createRouter({
	history: createWebHistory('/shop'),
	routes,
})

router.beforeEach(async (to) => {
	if (!session.isLoggedIn) {
		window.location.href = '/login?redirect-to=/shop'
		return false
	}
	const state = await fetchOnboardingState()
	if (!state.onboarding_complete && to.name !== 'Onboarding') {
		return { name: 'Onboarding' }
	}
	if (state.onboarding_complete && to.name === 'Onboarding') {
		return { name: 'Dashboard' }
	}
})

export default router

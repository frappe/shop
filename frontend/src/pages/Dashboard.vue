<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Dashboard</h1>
			<div class="flex items-center gap-2">
				<Button link="/">View store</Button>
				<Button link="/builder">Edit pages in Builder</Button>
			</div>
		</div>

		<div class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
			<div v-for="stat in stats" :key="stat.label" class="rounded-lg border border-outline-gray-1 p-4">
				<div class="text-sm text-ink-gray-5">{{ stat.label }}</div>
				<div class="mt-1 text-xl font-semibold text-ink-gray-9">{{ stat.value }}</div>
			</div>
		</div>

		<div class="mt-8">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="text-lg font-medium text-ink-gray-8">Recent orders</h2>
				<router-link to="/orders" class="text-base text-ink-gray-6 hover:text-ink-gray-8">
					View all
				</router-link>
			</div>
			<OrdersTable :orders="recentOrders.data || []" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createResource } from 'frappe-ui'

import OrdersTable from '@/components/OrdersTable.vue'

const dashboard = createResource({
	url: 'shop.api.admin.get_dashboard',
	auto: true,
})

const recentOrders = createResource({
	url: 'shop.api.admin.get_orders',
	params: { limit: 5 },
	auto: true,
})

const stats = computed(() => {
	const data = dashboard.data || {}
	return [
		{ label: 'Orders today', value: data.orders_today ?? '-' },
		{ label: 'Revenue (7 days)', value: data.revenue_week ?? '-' },
		{ label: 'Active carts', value: data.active_carts ?? '-' },
		{ label: 'Published products', value: data.published_products ?? '-' },
	]
})
</script>

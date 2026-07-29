<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Orders</h1>
			<div class="w-48">
				<FormControl v-model="statusFilter" type="select" :options="statusOptions" />
			</div>
		</div>
		<div class="mt-6">
			<OrdersTable :orders="orders.data || []" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { FormControl, createResource } from 'frappe-ui'

import OrdersTable from '@/components/OrdersTable.vue'

const statusFilter = ref('')
const statusOptions = [
	{ label: 'All statuses', value: '' },
	{ label: 'Draft', value: 'Draft' },
	{ label: 'To Deliver and Bill', value: 'To Deliver and Bill' },
	{ label: 'Completed', value: 'Completed' },
	{ label: 'Cancelled', value: 'Cancelled' },
]

const orders = createResource({
	url: 'shop.api.admin.get_orders',
	makeParams: () => ({ status: statusFilter.value || undefined, limit: 100 }),
	auto: true,
})

watch(statusFilter, () => orders.reload())
</script>

<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Orders" />

		<UiFilterBar v-model="search" search-placeholder="Search orders" class="mt-6">
			<div class="w-44">
				<FormControl v-model="statusFilter" type="select" :options="statusOptions" />
			</div>
			<div class="w-36">
				<FormControl v-model="paymentFilter" type="select" :options="paymentOptions" />
			</div>
			<template #trailing>{{ totalLabel }}</template>
		</UiFilterBar>

		<UiDataTable
			class="mt-4"
			:columns="columns"
			:rows="orders.data?.orders || []"
			row-key="name"
			:loading="orders.loading"
			clickable
			@row-click="(row) => router.push(`/orders/${row.name}`)"
		>
			<template #cell-name="{ row }">
				<span class="font-medium text-ink-gray-8">{{ row.name }}</span>
			</template>
			<template #cell-status="{ row }">
				<UiStatusBadge :label="row.status" />
			</template>
			<template #cell-payment_status="{ row }">
				<UiStatusBadge :label="row.payment_status" />
			</template>
			<template #cell-fulfillment_status="{ row }">
				<UiStatusBadge :label="row.fulfillment_status" />
			</template>
			<template #cell-formatted_total="{ row }">
				<span class="text-ink-gray-8">{{ row.formatted_total }}</span>
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideShoppingCart"
					title="No orders found"
					message="Try changing the filters, or wait for your first order to come in."
				/>
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="pageSize" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { FormControl, createResource, toast } from 'frappe-ui'
import { useRoute, useRouter } from 'vue-router'

import LucideShoppingCart from '~icons/lucide/shopping-cart'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiFilterBar from '@/components/UiFilterBar.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate } from '@/utils/format'

const pageSize = 20

const route = useRoute()
const router = useRouter()

const search = ref('')
const statusFilter = ref((route.query.status as string) || '')
const paymentFilter = ref('')
const start = ref(0)

const paymentOptions = [
	{ label: 'All payments', value: '' },
	{ label: 'Paid', value: 'Paid' },
	{ label: 'Unpaid', value: 'Unpaid' },
]

const orders = createResource({
	url: 'shop.api.orders.get_orders',
	makeParams: () => ({
		status: statusFilter.value || undefined,
		payment: paymentFilter.value || undefined,
		search: search.value || undefined,
		start: start.value,
		limit: pageSize,
	}),
	auto: true,
	onError: () => toast.error('Could not load orders'),
})

watch([statusFilter, paymentFilter, search], () => {
	start.value = 0
	orders.reload()
})
watch(start, () => orders.reload())

const statusOptions = computed(() => {
	const statuses: string[] = orders.data?.statuses || []
	return [
		{ label: 'All statuses', value: '' },
		...statuses.map((status) => ({ label: status, value: status })),
	]
})

const total = computed(() => orders.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'order' : 'orders'}`)

const columns = [
	{ key: 'name', label: 'Order' },
	{ key: 'customer_name', label: 'Customer' },
	{ key: 'transaction_date', label: 'Date', format: formatDate },
	{ key: 'status', label: 'Status' },
	{ key: 'payment_status', label: 'Payment' },
	{ key: 'fulfillment_status', label: 'Fulfillment' },
	{ key: 'formatted_total', label: 'Total', align: 'right' as const },
]
</script>

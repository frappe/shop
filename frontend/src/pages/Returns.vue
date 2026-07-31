<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Returns" subtitle="Return and replacement requests from your customers." />

		<div class="mt-6 flex flex-wrap items-center justify-between gap-3">
			<TabButtons v-model="status" :options="statusTabs" />
			<span class="text-sm text-ink-gray-5">{{ totalLabel }}</span>
		</div>

		<div v-if="requests.error" class="mt-6 flex flex-col items-center gap-3 py-16 text-center">
			<p class="text-p-base text-ink-red-8">{{ errorMessage }}</p>
			<Button @click="requests.reload()">Try again</Button>
		</div>

		<UiDataTable
			v-else
			class="mt-4"
			:columns="columns"
			:rows="rows"
			row-key="name"
			:loading="!requests.fetched"
		>
			<template #cell-name="{ row }">
				<div class="font-medium text-ink-gray-8">{{ row.name }}</div>
				<div class="text-sm text-ink-gray-5">{{ formatDate(row.creation) }}</div>
			</template>
			<template #cell-sales_order="{ row }">
				<router-link
					:to="`/orders/${row.sales_order}`"
					class="font-medium text-ink-gray-8 hover:underline"
				>
					{{ row.sales_order }}
				</router-link>
			</template>
			<template #cell-customer="{ row }">
				<div class="max-w-[9rem] truncate" :title="row.customer">{{ row.customer }}</div>
			</template>
			<template #cell-item_name="{ row }">
				<div class="max-w-[9rem] truncate" :title="row.item_name">{{ row.item_name }}</div>
			</template>
			<template #cell-reason="{ row }">
				<div class="max-w-[7rem] truncate" :title="row.reason">{{ row.reason || '-' }}</div>
			</template>
			<template #cell-status="{ row }">
				<UiStatusBadge :label="row.status" />
			</template>
			<template #cell-actions="{ row }">
				<ReturnRequestActions compact :request="row" @updated="requests.reload()" />
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideUndo2"
					title="No return requests"
					message="Customers can request returns from their order page once shipped."
				/>
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="PAGE_SIZE" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, createResource } from 'frappe-ui'

import LucideUndo2 from '~icons/lucide/undo-2'

import ReturnRequestActions from '@/components/ReturnRequestActions.vue'
import type { ReturnRequest } from '@/components/ReturnsPanel.vue'
import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate } from '@/utils/format'

const PAGE_SIZE = 20

const STATUSES = ['Requested', 'Approved', 'Rejected', 'Completed']

const statusTabs = [
	{ label: 'All', value: '' },
	...STATUSES.map((name) => ({ label: name, value: name })),
]

const status = ref('')
const start = ref(0)

const requests = createResource({
	url: 'shop.api.returns.get_requests',
	makeParams: () => ({
		status: status.value || undefined,
		start: start.value,
		limit: PAGE_SIZE,
	}),
	auto: true,
})

const rows = computed<ReturnRequest[]>(() => requests.data?.requests || [])
const total = computed(() => requests.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'request' : 'requests'}`)

const errorMessage = computed(() => {
	const error = requests.error as { messages?: string[]; message?: string } | null
	return error?.messages?.[0] || error?.message || 'Could not load return requests'
})

watch(status, () => {
	start.value = 0
	requests.reload()
})
watch(start, () => requests.reload())

const columns = [
	{ key: 'name', label: 'Request' },
	{ key: 'sales_order', label: 'Order' },
	{ key: 'customer', label: 'Customer' },
	{ key: 'item_name', label: 'Item' },
	{ key: 'request_type', label: 'Type' },
	{ key: 'reason', label: 'Reason' },
	{ key: 'status', label: 'Status' },
	{ key: 'actions', label: '', align: 'right' as const },
]
</script>

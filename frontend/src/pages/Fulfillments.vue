<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Fulfillments" subtitle="Every order handed to a fulfillment provider." />

		<div class="mt-6 flex flex-wrap items-center justify-between gap-3">
			<TabButtons v-model="status" :options="statusTabs" />
			<span class="text-sm text-ink-gray-5">{{ totalLabel }}</span>
		</div>

		<div v-if="shipments.error" class="mt-6 flex flex-col items-center gap-3 py-16 text-center">
			<p class="text-base text-ink-red-8">{{ errorMessage }}</p>
			<Button @click="shipments.reload()">Try again</Button>
		</div>

		<UiDataTable
			v-else
			class="mt-4"
			:columns="columns"
			:rows="rows"
			row-key="name"
			:loading="!shipments.fetched"
		>
			<template #cell-sales_order="{ row }">
				<router-link
					:to="`/orders/${row.sales_order}`"
					class="font-medium text-ink-gray-8 hover:underline"
				>
					{{ row.sales_order }}
				</router-link>
			</template>
			<template #cell-status="{ row }">
				<FulfillmentStatusBadge :status="row.status" />
			</template>
			<template #cell-carrier="{ row }">
				{{ row.carrier || '-' }}
			</template>
			<template #cell-tracking_number="{ row }">
				<a
					v-if="row.tracking_url && row.tracking_number"
					:href="row.tracking_url"
					target="_blank"
					class="inline-flex items-center gap-1 text-ink-gray-8 underline hover:text-ink-gray-9"
				>
					{{ row.tracking_number }}
					<LucideExternalLink class="size-3.5" />
				</a>
				<span v-else>{{ row.tracking_number || '-' }}</span>
			</template>
			<template #cell-requested_on="{ row }">
				{{ formatDate(row.requested_on) }}
			</template>
			<template #cell-actions="{ row }">
				<Tooltip text="Refresh status">
					<Button variant="ghost" :loading="syncing === row.name" @click="refresh(row)">
						<template #icon><LucideRefreshCw class="size-4" /></template>
					</Button>
				</Tooltip>
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideTruck"
					title="No shipments here"
					:message="emptyMessage"
				/>
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="PAGE_SIZE" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, Tooltip, call, createResource, toast } from 'frappe-ui'

import LucideExternalLink from '~icons/lucide/external-link'
import LucideRefreshCw from '~icons/lucide/refresh-cw'
import LucideTruck from '~icons/lucide/truck'

import FulfillmentStatusBadge from '@/components/FulfillmentStatusBadge.vue'
import type { FulfillmentSummary } from '@/components/FulfillmentPanel.vue'
import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'

const PAGE_SIZE = 20

const STATUSES = ['Pending', 'Accepted', 'Shipped', 'Delivered', 'Cancelled', 'Failed']

const statusTabs = [
	{ label: 'All', value: '' },
	...STATUSES.map((name) => ({ label: name, value: name })),
]

const status = ref('')
const start = ref(0)
const syncing = ref('')

const shipments = createResource({
	url: 'shop.api.fulfillment.list_fulfillments',
	makeParams: () => ({
		status: status.value || undefined,
		start: start.value,
		limit: PAGE_SIZE,
	}),
	auto: true,
})

const rows = computed<FulfillmentSummary[]>(() => shipments.data?.fulfillments || [])
const total = computed(() => shipments.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'shipment' : 'shipments'}`)

const emptyMessage = computed(() =>
	status.value
		? `No shipments are ${status.value.toLowerCase()} right now.`
		: 'Orders you send for fulfillment show up here with their tracking details.',
)

const errorMessage = computed(() => {
	const error = shipments.error as { messages?: string[]; message?: string } | null
	return error?.messages?.[0] || error?.message || 'Could not load fulfillments'
})

watch(status, () => {
	start.value = 0
	shipments.reload()
})
watch(start, () => shipments.reload())

const columns = [
	{ key: 'sales_order', label: 'Order' },
	{ key: 'provider_label', label: 'Provider' },
	{ key: 'status', label: 'Status' },
	{ key: 'carrier', label: 'Carrier' },
	{ key: 'tracking_number', label: 'Tracking' },
	{ key: 'requested_on', label: 'Requested' },
	{ key: 'actions', label: '', align: 'right' as const },
]

function formatDate(value?: string) {
	if (!value) return '-'
	const parsed = new Date(value.replace(' ', 'T'))
	if (Number.isNaN(parsed.getTime())) return value
	return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function refresh(row: FulfillmentSummary) {
	syncing.value = row.name
	try {
		await call('shop.api.fulfillment.sync_fulfillment', { fulfillment: row.name })
		toast.success('Status refreshed')
		shipments.reload()
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not refresh the shipment status')
	} finally {
		syncing.value = ''
	}
}
</script>

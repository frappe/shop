<template>
	<section v-if="rows.length" class="rounded-lg border border-outline-gray-1 p-4">
		<h2 class="text-base font-medium text-ink-gray-8">Returns</h2>
		<ul class="mt-3 divide-y divide-outline-gray-1">
			<li v-for="row in rows" :key="row.name" class="py-3 first:pt-0 last:pb-0">
				<div class="flex items-center justify-between gap-2">
					<span class="truncate text-base text-ink-gray-8">
						{{ row.item_name }} x {{ row.qty }}
					</span>
					<UiStatusBadge :label="row.status" />
				</div>
				<div class="mt-0.5 text-sm text-ink-gray-5">
					{{ row.request_type }}, {{ formatDate(row.creation) }}
				</div>
				<p v-if="row.reason" class="mt-1 text-p-sm text-ink-gray-6">{{ row.reason }}</p>
				<p v-if="row.resolution_note" class="mt-1 text-p-sm text-ink-gray-5">
					Note: {{ row.resolution_note }}
				</p>
				<ReturnRequestActions class="mt-2" :request="row" @updated="requests.reload()" />
			</li>
		</ul>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createResource } from 'frappe-ui'

import ReturnRequestActions from '@/components/ReturnRequestActions.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'
import { formatDate } from '@/utils/format'

export interface ReturnRequest {
	name: string
	item_name: string
	qty: number
	request_type: string
	status: string
	reason?: string
	resolution_note?: string
	creation: string
	sales_order?: string
	customer?: string
	item_code?: string
}

const props = defineProps<{ order: string }>()

const requests = createResource({
	url: 'shop.api.returns.for_order',
	makeParams: () => ({ order: props.order }),
	auto: true,
})

const rows = computed<ReturnRequest[]>(() => requests.data || [])
</script>

<template>
	<section class="rounded-lg border border-outline-gray-1 p-4">
		<h2 class="text-base font-medium text-ink-gray-8">Fulfillment</h2>

		<div v-if="loading" class="mt-4 space-y-2">
			<div class="h-4 w-1/3 animate-pulse rounded bg-surface-gray-2" />
			<div class="h-4 w-2/3 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<div v-else-if="parcels.error" class="mt-4 flex flex-wrap items-center gap-3">
			<p class="text-p-base text-ink-red-8">{{ errorMessage }}</p>
			<Button @click="parcels.reload()">Try again</Button>
		</div>

		<p v-else-if="!list.length" class="mt-3 text-p-base text-ink-gray-6">Nothing in this order is sent.</p>

		<div v-else class="mt-3 divide-y divide-outline-gray-1">
			<FulfillmentParcel
				v-for="(parcel, index) in list"
				:key="parcel.warehouse || index"
				class="py-3 first:pt-0 last:pb-0"
				:order="order"
				:docstatus="docstatus"
				:parcel="parcel"
				:providers="providers.data || []"
				:title="list.length > 1 ? parcelTitle(parcel, index) : undefined"
				@changed="changed"
			/>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createResource } from 'frappe-ui'

import FulfillmentParcel, { type Parcel } from '@/components/FulfillmentParcel.vue'

export type { FulfillmentSummary } from '@/components/FulfillmentParcel.vue'

const props = defineProps<{ order: string; docstatus: number }>()
const emit = defineEmits<{ changed: [] }>()

const parcels = createResource({
	url: 'shop.api.fulfillment.get_parcels',
	makeParams: () => ({ order: props.order }),
	auto: true,
})

const providers = createResource({ url: 'shop.api.fulfillment.get_providers', auto: true })

const list = computed<Parcel[]>(() => parcels.data || [])
const loading = computed(() => !parcels.fetched && !parcels.error)

const errorMessage = computed(() => {
	const error = parcels.error as { messages?: string[]; message?: string } | null
	return error?.messages?.[0] || error?.message || 'Could not load fulfillment details'
})

function parcelTitle(parcel: Parcel, index: number) {
	const from = parcel.warehouse_label ? ` · from ${parcel.warehouse_label}` : ''
	return `Parcel ${index + 1} of ${list.value.length}${from}`
}

function changed() {
	parcels.reload()
	emit('changed')
}
</script>

<template>
	<div class="mt-4 rounded border border-outline-gray-1 p-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="min-w-0 text-sm">
				<div class="text-ink-gray-5">Courier</div>
				<div class="text-base text-ink-gray-8">
					<template v-if="courier.booked">
						{{ [courier.provider, courier.service].filter(Boolean).join(': ') }}
						<span v-if="courier.formatted_amount" class="text-ink-gray-5">
							&middot; {{ courier.formatted_amount }}
						</span>
					</template>
					<template v-else>Not booked yet</template>
				</div>
				<div v-if="courier.booked" class="text-ink-gray-5">
					{{ courier.labels ? 'Label printed' : 'No label yet' }}
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				<Button v-if="courier.can_book && open" variant="solid" @click="openBooking">
					Book courier
				</Button>
				<Button
					v-if="courier.can_print_label"
					:variant="courier.labels ? 'subtle' : 'solid'"
					:loading="printing"
					@click="courier.labels ? openLabels() : confirmPrint()"
				>
					<template #prefix><LucidePrinter class="size-3.5" /></template>
					{{ courier.labels ? 'Open label' : 'Print label' }}
				</Button>
			</div>
		</div>

		<Dialog
			v-model="booking"
			:options="{
				title: 'Book courier',
				actions: [
					{
						label: chosen ? `Book for ${chosen.formatted_amount}` : 'Book',
						variant: 'solid',
						disabled: !chosen,
						loading: saving,
						onClick: book,
					},
				],
			}"
		>
			<div v-if="services.loading" class="flex justify-center py-8"><Spinner class="size-5" /></div>
			<p v-else-if="services.error" class="text-p-sm text-ink-red-8">
				{{ errorMessage(services.error, 'Could not get the courier services') }}
			</p>
			<p v-else-if="!rows.length" class="text-p-sm text-ink-gray-6">
				No courier offers a service for this parcel. Check its address, weight and size in Desk.
			</p>
			<div v-else class="space-y-2">
				<label
					v-for="row in rows"
					:key="row.id"
					class="flex cursor-pointer items-center gap-3 rounded border p-3"
					:class="row.id === chosenId ? 'border-outline-gray-4 bg-surface-gray-1' : 'border-outline-gray-1'"
				>
					<input v-model="chosenId" type="radio" name="courier-service" :value="row.id" />
					<div class="min-w-0 flex-1">
						<div class="text-base text-ink-gray-8">{{ row.service }}</div>
						<div class="text-sm text-ink-gray-5">
							{{ [row.provider, row.carrier].filter(Boolean).join(' · ') }}
							<span v-if="row.preferred" class="ml-1 text-ink-green-7">Customer's choice</span>
						</div>
					</div>
					<div class="text-base font-medium text-ink-gray-8">{{ row.formatted_amount }}</div>
				</label>
				<p class="text-p-sm text-ink-gray-5">
					The courier charges for the booking. The parcel's Shipment is submitted if it is still a draft.
				</p>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, Spinner, call, createResource, dialog, toast } from 'frappe-ui'

import LucidePrinter from '~icons/lucide/printer'

export interface Courier {
	booked: boolean
	provider: string | null
	service: string | null
	amount: number | null
	formatted_amount?: string
	labels: number
	can_book: boolean
	can_print_label: boolean
}

interface CourierService {
	id: string
	provider: string
	carrier: string
	service: string
	amount: number
	formatted_amount: string
	preferred: boolean
}

const props = defineProps<{ fulfillment: string; courier: Courier; open: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const booking = ref(false)
const saving = ref(false)
const printing = ref(false)
const chosenId = ref('')

const services = createResource({
	url: 'shop.api.fulfillment.get_courier_services',
	makeParams: () => ({ fulfillment: props.fulfillment }),
	onSuccess: (data: CourierService[]) => {
		chosenId.value = (data.find((row) => row.preferred) || data[0])?.id || ''
	},
})
const rows = computed<CourierService[]>(() => services.data || [])
const chosen = computed(() => rows.value.find((row) => row.id === chosenId.value) || null)

function errorMessage(error: unknown, fallback: string) {
	const messages = (error as { messages?: string[] } | null)?.messages
	return messages?.[0] || fallback
}

function openBooking() {
	chosenId.value = ''
	booking.value = true
	services.reload()
}

async function book() {
	if (!chosen.value) return
	saving.value = true
	try {
		await call('shop.api.fulfillment.book_courier', {
			fulfillment: props.fulfillment,
			service_id: chosen.value.id,
		})
		booking.value = false
		toast.success(`Booked with ${chosen.value.service}`)
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, 'Could not book the courier'))
	} finally {
		saving.value = false
	}
}

function labelUrl(index: number) {
	const query = new URLSearchParams({ fulfillment: props.fulfillment, index: String(index) })
	return `/api/method/shop.api.fulfillment.label?${query}`
}

function openLabels(count = props.courier.labels, tab: Window | null = null) {
	for (let index = 0; index < count; index++) {
		if (index === 0 && tab) tab.location.href = labelUrl(0)
		else window.open(labelUrl(index), '_blank')
	}
}

function confirmPrint() {
	dialog.confirm({
		title: 'Print label',
		message: `Buy the label from ${props.courier.provider}? The courier charges for it. Opening it again later is free.`,
		confirmLabel: 'Print label',
		onConfirm: async () => {
			// opened now, while the click allows it, and pointed at the label once it is bought
			const tab = window.open('', '_blank')
			printing.value = true
			try {
				const result = (await call('shop.api.fulfillment.print_label', {
					fulfillment: props.fulfillment,
				})) as { labels: string[] }
				if (result.labels.length) openLabels(result.labels.length, tab)
				else tab?.close()
				toast.success('Label printed')
				emit('changed')
			} catch (error) {
				tab?.close()
				toast.error(errorMessage(error, 'Could not print the label'))
			} finally {
				printing.value = false
			}
		},
	})
}
</script>

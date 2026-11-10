<template>
	<Dialog v-model="show" :options="options">
		<template #body-content>
			<p class="text-base text-ink-gray-6">
				Record the shipment you packed yourself. Both fields are optional.
			</p>
			<div class="mt-4 space-y-4">
				<UiPicker
					v-model="carrier"
					label="Carrier"
					description="Who is delivering it. Choose one you've used, or type a new name."
					:options="carriers"
					placeholder="Choose or type a carrier"
					allow-custom
				/>
				<FormControl
					v-model="trackingNumber"
					label="Tracking number"
					description="From the carrier's label or receipt, so the customer can follow the parcel."
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, FormControl, call, toast } from 'frappe-ui'

import UiPicker from '@/components/UiPicker.vue'

const props = defineProps<{ fulfillment: string }>()
const emit = defineEmits<{ shipped: [] }>()

const show = defineModel<boolean>({ required: true })

const carrier = ref('')
const trackingNumber = ref('')
const carriers = ref<string[]>([])

watch(show, async (open) => {
	if (!open) return
	carrier.value = ''
	trackingNumber.value = ''
	carriers.value = await call('shop.api.fulfillment.get_carriers').catch(() => [])
})

const options = computed(() => ({
	title: 'Mark as shipped',
	size: 'sm',
	actions: [{ label: 'Mark shipped', variant: 'solid', onClick: markShipped }],
}))

async function markShipped() {
	try {
		await call('shop.api.fulfillment.mark_shipped', {
			fulfillment: props.fulfillment,
			carrier: carrier.value || undefined,
			tracking_number: trackingNumber.value || undefined,
		})
		toast.success('Shipment marked as shipped')
		emit('shipped')
		show.value = false
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not mark the shipment as shipped')
	}
}
</script>

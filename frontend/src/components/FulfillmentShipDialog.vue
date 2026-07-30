<template>
	<Dialog v-model="show" :options="options">
		<template #body-content>
			<p class="text-base text-ink-gray-6">
				Record the shipment you packed yourself. Both fields are optional.
			</p>
			<div class="mt-4 space-y-4">
				<FormControl v-model="carrier" label="Carrier" placeholder="Delhivery" />
				<FormControl v-model="trackingNumber" label="Tracking number" placeholder="AWB123456789" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, FormControl, call, toast } from 'frappe-ui'

const props = defineProps<{ fulfillment: string }>()
const emit = defineEmits<{ shipped: [] }>()

const show = defineModel<boolean>({ required: true })

const carrier = ref('')
const trackingNumber = ref('')

watch(show, (open) => {
	if (!open) return
	carrier.value = ''
	trackingNumber.value = ''
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

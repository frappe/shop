<template>
	<Dialog v-model="show" :options="options">
		<template #body-content>
			<FormControl
				v-model="note"
				type="textarea"
				label="Resolution note"
				placeholder="Optional note for your records"
			/>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, FormControl, call, toast } from 'frappe-ui'

const props = defineProps<{ request: string; status: 'Rejected' | 'Completed' }>()
const emit = defineEmits<{ updated: [] }>()

const show = defineModel<boolean>({ required: true })

const note = ref('')

watch(show, (open) => {
	if (open) note.value = ''
})

const labels = {
	Rejected: {
		title: 'Reject request',
		button: 'Reject',
		theme: 'red',
		success: 'Request rejected',
		failure: 'Could not reject the request',
	},
	Completed: {
		title: 'Mark completed',
		button: 'Mark completed',
		theme: 'gray',
		success: 'Request marked as completed',
		failure: 'Could not complete the request',
	},
} as const

const options = computed(() => ({
	title: labels[props.status].title,
	size: 'sm',
	actions: [
		{
			label: labels[props.status].button,
			variant: 'solid',
			theme: labels[props.status].theme,
			onClick: save,
		},
	],
}))

async function save() {
	try {
		await call('shop.api.returns.set_status', {
			name: props.request,
			status: props.status,
			note: note.value || undefined,
		})
		toast.success(labels[props.status].success)
		emit('updated')
		show.value = false
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || labels[props.status].failure)
	}
}
</script>

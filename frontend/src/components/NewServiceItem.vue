<template>
	<Button variant="ghost" size="sm" class="w-fit" @click="open">
		<template #prefix><LucidePlus class="size-3.5" /></template>
		New item
	</Button>
	<Dialog
		v-model="show"
		:options="{
			title: 'New item',
			actions: [{ label: 'Create', variant: 'solid', loading: creating, onClick: create }],
		}"
	>
		<div class="space-y-3">
			<FormControl v-model="name" label="Item name" required />
			<p class="text-p-sm text-ink-gray-5">
				A service item, not kept in stock. Its income account and taxes can be set on the item in Desk.
			</p>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'

import LucidePlus from '~icons/lucide/plus'

const props = defineProps<{ suggestion: string }>()
const emit = defineEmits<{ created: [name: string] }>()

const show = ref(false)
const creating = ref(false)
const name = ref('')

function open() {
	name.value = props.suggestion
	show.value = true
}

async function create() {
	if (!name.value.trim()) {
		toast.error('Item name is required')
		return
	}
	creating.value = true
	try {
		const item = await call('shop.api.settings.create_service_item', { item_name: name.value.trim() })
		emit('created', item)
		show.value = false
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not create the item')
	} finally {
		creating.value = false
	}
}
</script>

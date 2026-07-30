<template>
	<Autocomplete
		:model-value="selected"
		label="ERPNext item"
		placeholder="Search items by name or code"
		:options="options"
		@update:query="search"
		@update:model-value="pick"
	/>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Autocomplete, call, toast } from 'frappe-ui'

interface ItemOption {
	label: string
	value: string
	hasVariants: boolean
}

const emit = defineEmits<{ picked: [ItemOption] }>()

const selected = ref<ItemOption | null>(null)
const options = ref<ItemOption[]>([])
let timer: ReturnType<typeof setTimeout> | null = null

onMounted(() => search(''))

function search(query: string) {
	if (timer) clearTimeout(timer)
	timer = setTimeout(() => load(query), 250)
}

async function load(query: string) {
	try {
		const items = await call('shop.api.admin.search_items', { query })
		options.value = items.map((item: { name: string; item_name: string; has_variants: number }) => ({
			label: item.item_name || item.name,
			value: item.name,
			hasVariants: !!item.has_variants,
		}))
	} catch (error) {
		toast.error('Could not load items')
	}
}

function pick(option: ItemOption | null) {
	selected.value = option
	if (option) emit('picked', option)
}
</script>

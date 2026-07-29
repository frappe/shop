<template>
	<Dialog
		v-model="show"
		:options="{
			title: editName ? 'Edit product' : 'New product',
			actions: [
				{
					label: editName ? 'Save' : 'Create',
					variant: 'solid',
					onClick: save,
				},
			],
		}"
	>
		<div class="space-y-4">
			<Autocomplete
				v-if="!editName"
				v-model="selectedItem"
				label="Item"
				placeholder="Search items"
				:options="itemOptions"
				@update:query="searchItems"
			/>
			<div v-else>
				<div class="text-sm text-ink-gray-5">Slug</div>
				<div class="mt-1 text-base text-ink-gray-7">{{ form.slug || 'Not set' }}</div>
			</div>
			<FormControl v-model="form.product_name" label="Product name" />
			<FormControl v-model="form.short_description" type="textarea" label="Short description" />
			<template v-if="editName">
				<Autocomplete
					v-model="selectedCollections"
					label="Collections"
					placeholder="Select collections"
					:options="collectionOptions"
					multiple
				/>
				<FormControl v-model="form.ranking" type="number" label="Ranking" />
			</template>
			<FormControl v-model="form.published" type="checkbox" label="Published" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Autocomplete, Dialog, FormControl, call, createListResource, toast } from 'frappe-ui'

interface Option {
	label: string
	value: string
}

const props = defineProps<{
	editName: string | null
	list: ReturnType<typeof createListResource>
}>()

const show = defineModel<boolean>({ required: true })

const form = reactive({
	product_name: '',
	short_description: '',
	published: false,
	ranking: 0,
	slug: '',
})
const selectedItem = ref<Option | null>(null)
const selectedCollections = ref<Option[]>([])
const itemOptions = ref<Option[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null

const collections = createListResource({
	doctype: 'Shop Collection',
	fields: ['name', 'title'],
	pageLength: 100,
})

const collectionOptions = computed<Option[]>(() =>
	(collections.data || []).map((c: { name: string; title: string }) => ({
		label: c.title,
		value: c.name,
	})),
)

watch(show, (open) => {
	if (open) resetAndLoad()
})

async function resetAndLoad() {
	Object.assign(form, {
		product_name: '',
		short_description: '',
		published: false,
		ranking: 0,
		slug: '',
	})
	selectedItem.value = null
	selectedCollections.value = []
	if (!props.editName) {
		searchItems('')
		return
	}
	await collections.fetch()
	const doc = await call('frappe.client.get', {
		doctype: 'Shop Product',
		name: props.editName,
	})
	Object.assign(form, {
		product_name: doc.product_name || '',
		short_description: doc.short_description || '',
		published: !!doc.published,
		ranking: doc.ranking || 0,
		slug: doc.slug || '',
	})
	selectedCollections.value = (doc.collections || []).map((row: { collection: string }) => ({
		label: collectionOptions.value.find((c) => c.value === row.collection)?.label || row.collection,
		value: row.collection,
	}))
}

function searchItems(query: string) {
	if (searchTimer) clearTimeout(searchTimer)
	searchTimer = setTimeout(async () => {
		const items = await call('shop.api.admin.search_items', { query })
		itemOptions.value = items.map((item: { name: string; item_name: string }) => ({
			label: item.item_name || item.name,
			value: item.name,
		}))
	}, 250)
}

watch(selectedItem, (item) => {
	if (item && !form.product_name) form.product_name = item.label
})

async function save() {
	try {
		if (props.editName) {
			await props.list.setValue.submit({
				name: props.editName,
				product_name: form.product_name,
				short_description: form.short_description,
				published: form.published ? 1 : 0,
				ranking: Number(form.ranking) || 0,
				collections: selectedCollections.value.map((c) => ({ collection: c.value })),
			})
			toast.success('Product updated')
		} else {
			if (!selectedItem.value) {
				toast.error('Select an item first')
				return
			}
			await props.list.insert.submit({
				item: selectedItem.value.value,
				product_name: form.product_name,
				short_description: form.short_description,
				published: form.published ? 1 : 0,
			})
			toast.success('Product created')
		}
		show.value = false
	} catch (error) {
		toast.error('Could not save product')
	}
}
</script>
